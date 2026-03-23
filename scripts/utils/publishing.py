from __future__ import annotations

import html
import json
import re
from pathlib import Path
from urllib.parse import urlparse


ASCII_HEAVY_RE = re.compile(r"^[\x00-\x7F\s'\";,.!?()\-_/&%:]+$")
ORDERED_LIST_RE = re.compile(r"^(\d+)\.\s+(.*)$")
IMAGE_MARKDOWN_RE = re.compile(r"^!\[(.*?)\]\((.*?)\)$")
CJK_RE = re.compile(r"[\u3400-\u9fff]")
GENERATED_TAIL_HEADINGS = {"信息来源", "相关资源", "结束语"}


def _optional_text(value: object, *, default: str = "") -> str:
    if value is None:
        return default
    normalized = str(value).strip()
    if not normalized or normalized.lower() == "none":
        return default
    return normalized


def _normalize_src(value: str) -> str:
    return value.replace("\\", "/")


def _contains_cjk(text: str) -> bool:
    return bool(CJK_RE.search(text))


def _is_youtube_url(url: str) -> bool:
    parsed = urlparse(url)
    netloc = parsed.netloc.lower()
    return "youtube.com" in netloc or "youtu.be" in netloc


def trim_cover_copy(text: str, limit: int = 26) -> str:
    stripped = text.strip()
    if not stripped or limit <= 0 or len(stripped) <= limit:
        return stripped

    punctuation = "，。！？；：,.!?;:"
    for index in range(limit, min(len(stripped), limit + 8)):
        if stripped[index] in punctuation:
            return stripped[:index].rstrip(punctuation)

    best_break = max((stripped.rfind(mark, 0, limit) for mark in punctuation), default=-1)
    if best_break >= max(8, limit // 2):
        return stripped[:best_break].rstrip(punctuation)
    return stripped[:limit].rstrip(punctuation)


def _looks_like_english_fallback(text: str) -> bool:
    stripped = text.strip()
    if not stripped or _contains_cjk(stripped):
        return False
    if len(stripped) < 24:
        return False
    return bool(ASCII_HEAVY_RE.match(stripped))


def sanitize_markdown(markdown_text: str) -> str:
    sanitized_lines: list[str] = []
    for raw_line in markdown_text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = raw_line.rstrip()
        content = line[2:].strip() if line.startswith("- ") else line.strip("# ").strip()
        if _looks_like_english_fallback(content):
            continue
        sanitized_lines.append(line)
    return "\n".join(sanitized_lines).strip()


def _clean_entry(item: dict) -> dict:
    return {
        "video_id": _optional_text(item.get("video_id")),
        "title": _optional_text(item.get("title"), default="未命名来源"),
        "url": _optional_text(item.get("url")),
        "channel_title": _optional_text(item.get("channel_title")),
        "published_at": item.get("published_at"),
    }


def build_reference_videos(source_notes: list[dict] | None) -> list[dict]:
    if not source_notes:
        return []

    references: list[dict] = []
    seen: set[tuple[str, str, str]] = set()
    for item in source_notes:
        cleaned = _clean_entry(item)
        if not cleaned["url"] and not cleaned["video_id"]:
            continue
        if not (cleaned["video_id"] or _is_youtube_url(cleaned["url"])):
            continue
        key = (cleaned["video_id"], cleaned["url"], cleaned["title"])
        if key in seen:
            continue
        seen.add(key)
        references.append(cleaned)
    return references


def build_reference_entries(source_notes: list[dict] | None, reference_videos: list[dict] | None) -> list[dict]:
    merged: list[dict] = []
    seen: set[tuple[str, str, str]] = set()

    for collection in (reference_videos or [], source_notes or []):
        for item in collection:
            cleaned = _clean_entry(item)
            if not cleaned["url"] and not cleaned["video_id"]:
                continue
            if not (cleaned["video_id"] or _is_youtube_url(cleaned["url"])):
                continue
            key = (cleaned["video_id"], cleaned["url"], cleaned["title"])
            if key in seen:
                continue
            seen.add(key)
            merged.append(cleaned)

    return merged


def _default_resource_title(item: dict, url: str) -> str:
    title = _optional_text(item.get("title"))
    if title and not all(ch == "?" for ch in title):
        return title
    entity = _optional_text(item.get("entity"))
    source_type = _optional_text(item.get("type"))
    if entity and source_type == "official_candidate":
        return f"{entity} \u5b98\u65b9\u8d44\u6e90"
    if entity:
        return f"{entity} \u76f8\u5173\u8d44\u6e90"
    parsed = urlparse(url)
    return parsed.netloc or "\u76f8\u5173\u8d44\u6e90"


def _default_resource_channel_title(item: dict) -> str:
    source_type = _optional_text(item.get("type"))
    if source_type == "description_link":
        return "\u89c6\u9891\u63cf\u8ff0\u94fe\u63a5"
    if source_type == "official_candidate":
        return "\u5b98\u65b9\u5019\u9009"
    return "\u76f8\u5173\u8d44\u6e90"


def build_resource_links(source_notes: list[dict] | None, reference_entries: list[dict] | None = None) -> list[dict]:
    if not source_notes:
        return []

    reference_urls = {_optional_text(item.get("url")) for item in (reference_entries or [])}
    resources: list[dict] = []
    seen_urls: set[str] = set()

    def append_resource(raw_item: dict, *, default_channel_title: str = "") -> None:
        url = _optional_text(raw_item.get("url"))
        if not url or url in seen_urls or url in reference_urls:
            return
        if _is_youtube_url(url) or _optional_text(raw_item.get("video_id")):
            return
        seen_urls.add(url)
        resources.append({
            "video_id": "",
            "title": _default_resource_title(raw_item, url),
            "url": url,
            "channel_title": _optional_text(
                raw_item.get("channel_title"),
                default=default_channel_title or _default_resource_channel_title(raw_item),
            ),
            "published_at": raw_item.get("published_at"),
        })

    nested_sources: list[dict] = []
    for item in source_notes:
        cleaned = _clean_entry(item)
        url = cleaned["url"]
        if url and not _is_youtube_url(url) and not cleaned["video_id"]:
            append_resource(cleaned)
        nested_sources.extend(item.get("sources", []))

    for source in nested_sources:
        if _optional_text(source.get("type")) == "description_link":
            append_resource(source)

    for source in nested_sources:
        if _optional_text(source.get("type")) != "description_link":
            append_resource(source)

    return resources

def build_headline_bundle(article: dict) -> dict:
    topic = article.get("task", {}).get("topic") or "AI"
    base_title = article.get("final_title") or article.get("selected_title") or f"{topic} 观察"
    title_candidates = [
        base_title,
        f"{topic} 值得关注的模型清单",
        f"围绕 {topic} 的一线产品变化",
        f"{topic} 的模型分工图",
    ]
    digest = article.get("digest") or f"围绕 {topic} 的模型、产品和工作流做一线拆解。"
    return {
        "task": article.get("task", {}),
        "article_type": article.get("article_type"),
        "selected_title": base_title,
        "title_candidates": title_candidates,
        "digest": digest,
        "cover_copy": trim_cover_copy(article.get("cover_copy") or base_title),
        "body_markdown": sanitize_markdown(article.get("body_markdown", "")),
        "source_notes": article.get("source_notes", []),
        "reference_videos": build_reference_videos(article.get("source_notes", [])),
        "review_flags": article.get("review_flags", []),
    }


def _paragraph_html(text: str) -> str:
    return (
        '<p style="margin: 0 0 16px; line-height: 1.9; font-size: 16px; color: #1f2937;">'
        + html.escape(text)
        + "</p>"
    )


def _heading_html(text: str, level: int) -> str:
    if level == 1:
        size = "30px"
        margin_top = "0"
    elif level == 2:
        size = "22px"
        margin_top = "32px"
    else:
        size = "18px"
        margin_top = "24px"
    return (
        f'<h{level} style="margin: {margin_top} 0 14px; line-height: 1.4; font-size: {size}; color: #111827;">'
        f"{html.escape(text)}"
        f"</h{level}>"
    )


def _list_item_html(text: str) -> str:
    return (
        '<li style="margin: 0 0 10px; line-height: 1.85; font-size: 16px; color: #1f2937;">'
        + html.escape(text)
        + "</li>"
    )


def _figure_html(src: str, caption: str = "") -> str:
    safe_src = html.escape(_normalize_src(src))
    safe_caption = html.escape(caption or "")
    image_html = (
        '<figure style="margin: 24px 0;">'
        f'<img src="{safe_src}" alt="{safe_caption}" style="width: 100%; height: auto; border-radius: 12px; display: block;" />'
    )
    if caption:
        image_html += (
            f'<figcaption style="margin-top: 8px; font-size: 13px; color: #64748b; text-align: center;">'
            f"{safe_caption}</figcaption>"
        )
    image_html += "</figure>"
    return image_html


def _blockquote_html(lines: list[str]) -> str:
    quote = "<br />".join(html.escape(item) for item in lines)
    return (
        '<blockquote style="margin: 20px 0; padding: 12px 16px; border-left: 4px solid #cbd5e1; background: #f8fafc; color: #334155; line-height: 1.85; font-size: 15px;">'
        + quote
        + "</blockquote>"
    )


def _format_meta_line(prefix: str, value: object) -> str:
    text = _optional_text(value)
    return f"{prefix}{text}" if text else ""


def build_reference_section_markdown(reference_entries: list[dict]) -> str:
    lines = ["## 信息来源", ""]
    if not reference_entries:
        lines.append("暂无可展示的信息来源。")
        return "\n".join(lines)

    for index, item in enumerate(reference_entries, 1):
        title = _optional_text(item.get("title"), default="未命名来源")
        channel_title = _format_meta_line("来源：", item.get("channel_title"))
        published_at = _format_meta_line("日期：", item.get("published_at"))
        url = _format_meta_line("地址：", item.get("url"))
        parts = [part for part in (channel_title, published_at, url) if part]
        suffix = " | ".join(parts)
        lines.append(f"{index}. {title}" + (f" | {suffix}" if suffix else ""))
    return "\n".join(lines)


def build_resource_links_section_markdown(resource_links: list[dict]) -> str:
    lines = ["## 相关资源", ""]
    if not resource_links:
        lines.append("暂无补充相关资源。")
        return "\n".join(lines)

    for index, item in enumerate(resource_links, 1):
        title = _optional_text(item.get("title"), default="未命名资源")
        channel_title = _format_meta_line("来源：", item.get("channel_title"))
        published_at = _format_meta_line("日期：", item.get("published_at"))
        url = _format_meta_line("地址：", item.get("url"))
        parts = [part for part in (channel_title, published_at, url) if part]
        suffix = " | ".join(parts)
        lines.append(f"{index}. {title}" + (f" | {suffix}" if suffix else ""))
    return "\n".join(lines)


def resolve_qrcode_src(skill_dir: Path, brand_config: dict) -> str:
    configured = _optional_text(brand_config.get("qrcode_url"))
    if not configured:
        return ""

    configured_path = Path(configured)
    if configured_path.exists():
        return _normalize_src(str(configured_path))

    if configured_path.name:
        candidate = skill_dir / "assets" / configured_path.name
        if candidate.exists():
            return _normalize_src(str(candidate))

    return _normalize_src(configured)


def build_footer_section_markdown(skill_dir: Path, brand_config: dict) -> str:
    follow_text = _optional_text(brand_config.get("follow_text"))
    qrcode_src = resolve_qrcode_src(skill_dir, brand_config)
    if not follow_text and not qrcode_src:
        return ""

    lines = ["## 结束语", ""]
    if follow_text:
        lines.extend(line.strip() for line in follow_text.splitlines() if line.strip())
        lines.append("")
    if qrcode_src:
        safe_src = html.escape(_normalize_src(qrcode_src), quote=True)
        lines.append(
            '<p style="margin: 16px 0 0;">'
            f'<img src="{safe_src}" alt="公众号二维码" '
            'style="width: 220px; max-width: 100%; height: auto; display: block; border: 0; border-radius: 0; box-shadow: none;" />'
            '</p>'
        )
    return "\n".join(lines).strip()

def _build_image_lookup(image_package: dict | None) -> tuple[dict | None, dict[str, dict], dict | None]:
    if not image_package:
        return None, {}, None

    generated = {item.get("asset_id"): item for item in image_package.get("generated_assets", [])}
    cover_request = image_package.get("cover_request") or None
    cover = None
    if cover_request:
        cover = {**cover_request, **generated.get(cover_request.get("asset_id"), {})}

    inline_lookup: dict[str, dict] = {}
    for request in image_package.get("inline_requests", []):
        key = _optional_text(request.get("section_heading"))
        if not key:
            continue
        inline_lookup[key] = {**request, **generated.get(request.get("asset_id"), {})}

    infographic_request = image_package.get("infographic_request") or None
    infographic = None
    if infographic_request:
        infographic = {**infographic_request, **generated.get(infographic_request.get("asset_id"), {})}

    return cover, inline_lookup, infographic


def _image_src(item: dict | None) -> str:
    if not item:
        return ""
    return _normalize_src(_optional_text(item.get("path")) or _optional_text(item.get("url")))


def _image_markdown_line(src: str) -> str:
    return f"![]({_normalize_src(src)})"


def inject_image_markdown(markdown_text: str, image_package: dict | None = None) -> str:
    text = markdown_text.strip()
    if not image_package or not text:
        return text

    if any(IMAGE_MARKDOWN_RE.match(line.strip()) for line in text.splitlines()):
        return text

    cover, inline_lookup, infographic = _build_image_lookup(image_package)
    lines = text.splitlines()
    output: list[str] = []
    h2_count = 0

    for raw_line in lines:
        output.append(raw_line)
        stripped = raw_line.strip()

        if stripped.startswith("# "):
            cover_src = _image_src(cover)
            if cover_src:
                output.extend(["", _image_markdown_line(cover_src), ""])
            continue

        if stripped.startswith("## "):
            h2_count += 1
            heading = stripped[3:].strip()
            image_item = inline_lookup.get(heading)
            image_src = _image_src(image_item)
            if image_src:
                output.extend(["", _image_markdown_line(image_src), ""])
            if infographic and h2_count == 3:
                infographic_src = _image_src(infographic)
                if infographic_src:
                    output.extend(["", "### \u4fe1\u606f\u56fe\u53c2\u8003", "", _image_markdown_line(infographic_src), ""])

    if infographic and h2_count < 3:
        infographic_src = _image_src(infographic)
        if infographic_src:
            output.extend(["", "### 信息图参考", "", _image_markdown_line(infographic_src)])

    return "\n".join(output).strip()


def strip_generated_tail_sections(markdown_text: str) -> str:
    lines = markdown_text.splitlines()
    output: list[str] = []
    for raw_line in lines:
        stripped = raw_line.strip()
        if stripped.startswith("## "):
            heading = stripped[3:].strip()
            if heading in GENERATED_TAIL_HEADINGS:
                break
        output.append(raw_line)
    return "\n".join(output).strip()


def build_complete_markdown(
    markdown_text: str,
    reference_entries: list[dict],
    resource_links: list[dict],
    skill_dir: Path,
    brand_config: dict,
) -> str:
    base = strip_generated_tail_sections(markdown_text)
    sections = [
        build_reference_section_markdown(reference_entries),
        build_resource_links_section_markdown(resource_links),
        build_footer_section_markdown(skill_dir, brand_config),
    ]
    non_empty = [section.strip() for section in sections if section and section.strip()]
    if not non_empty:
        return base
    if not base:
        return "\n\n".join(non_empty)
    return (base + "\n\n" + "\n\n".join(non_empty)).strip()


def markdown_to_html(markdown_text: str, image_package: dict | None = None) -> str:
    prepared = markdown_text.strip()
    if image_package and prepared and not any(IMAGE_MARKDOWN_RE.match(line.strip()) for line in prepared.splitlines()):
        prepared = inject_image_markdown(prepared, image_package=image_package)

    lines = prepared.splitlines()
    blocks: list[str] = []
    unordered_items: list[str] = []
    ordered_items: list[str] = []
    blockquote_lines: list[str] = []

    def flush_unordered() -> None:
        nonlocal unordered_items
        if unordered_items:
            blocks.append('<ul style="margin: 0 0 18px 22px; padding: 0;">' + "".join(unordered_items) + "</ul>")
            unordered_items = []

    def flush_ordered() -> None:
        nonlocal ordered_items
        if ordered_items:
            blocks.append('<ol style="margin: 0 0 18px 22px; padding-left: 20px;">' + "".join(ordered_items) + "</ol>")
            ordered_items = []

    def flush_blockquote() -> None:
        nonlocal blockquote_lines
        if blockquote_lines:
            blocks.append(_blockquote_html(blockquote_lines))
            blockquote_lines = []

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            flush_unordered()
            flush_ordered()
            flush_blockquote()
            continue

        if line == "---":
            flush_unordered()
            flush_ordered()
            flush_blockquote()
            blocks.append('<hr style="margin: 28px 0; border: 0; border-top: 1px solid #e2e8f0;" />')
            continue

        if line.startswith("<") and line.endswith(">"):
            flush_unordered()
            flush_ordered()
            flush_blockquote()
            blocks.append(raw_line)
            continue

        image_match = IMAGE_MARKDOWN_RE.match(line)
        if image_match:
            flush_unordered()
            flush_ordered()
            flush_blockquote()
            alt_text, src = image_match.groups()
            blocks.append(_figure_html(src, alt_text))
            continue

        if line.startswith("# "):
            flush_unordered()
            flush_ordered()
            flush_blockquote()
            blocks.append(_heading_html(line[2:].strip(), 1))
            continue

        if line.startswith("## "):
            flush_unordered()
            flush_ordered()
            flush_blockquote()
            blocks.append(_heading_html(line[3:].strip(), 2))
            continue

        if line.startswith("### "):
            flush_unordered()
            flush_ordered()
            flush_blockquote()
            blocks.append(_heading_html(line[4:].strip(), 3))
            continue

        if line.startswith("> "):
            flush_unordered()
            flush_ordered()
            blockquote_lines.append(line[2:].strip())
            continue

        if line.startswith("- "):
            flush_ordered()
            flush_blockquote()
            unordered_items.append(_list_item_html(line[2:].strip()))
            continue

        ordered_match = ORDERED_LIST_RE.match(line)
        if ordered_match:
            flush_unordered()
            flush_blockquote()
            ordered_items.append(_list_item_html(ordered_match.group(2).strip()))
            continue

        flush_unordered()
        flush_ordered()
        flush_blockquote()
        blocks.append(_paragraph_html(line))

    flush_unordered()
    flush_ordered()
    flush_blockquote()
    return "\n".join(blocks)


def render_template(template_text: str, values: dict[str, str]) -> str:
    rendered = template_text
    for key, value in values.items():
        rendered = rendered.replace(f"{{{{ {key} }}}}", value)
    return rendered


def build_formatted_article(bundle: dict, skill_dir: Path, image_package: dict | None = None) -> dict:
    template = (skill_dir / "assets" / "templates" / "article_shell.html").read_text(encoding="utf-8-sig")
    cleaned_markdown = sanitize_markdown(bundle.get("body_markdown", ""))
    prepared_markdown = inject_image_markdown(cleaned_markdown, image_package=image_package)
    body_html = markdown_to_html(prepared_markdown)
    article_html = render_template(
        template,
        {
            "title": html.escape(bundle.get("selected_title", "")),
            "summary": html.escape(bundle.get("digest", "")),
            "body_html": body_html,
        },
    )
    return {
        "task": bundle.get("task", {}),
        "article_type": bundle.get("article_type"),
        "title": bundle.get("selected_title", ""),
        "title_candidates": bundle.get("title_candidates", []),
        "digest": bundle.get("digest", ""),
        "cover_copy": bundle.get("cover_copy", ""),
        "body_markdown": prepared_markdown,
        "body_html": article_html,
        "image_package": image_package,
        "source_notes": bundle.get("source_notes", []),
        "reference_videos": bundle.get("reference_videos", []),
        "review_flags": bundle.get("review_flags", []),
    }


def load_brand_config(path: str | None) -> dict:
    defaults = {
        "author_name": "AI情报局",
        "author_bio": "专注跟踪 AI 产品、模型与工作流变化，输出适合中文读者快速理解的一线拆解。",
        "qrcode_url": "E:\project\CodexProject\SkillsDemo\.agents\skills\youtube-ai-to-wechat\assets\公众号二维码.png",
        "follow_text": "持续分享 AI 技术与编程工具干货，觉得有用就点个关注，不错过每一篇实用内容。",
    }
    if not path:
        return defaults
    loaded = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    section = loaded.get("brand", loaded)
    return {**defaults, **section}


def inject_blocks(formatted: dict, skill_dir: Path, brand_config: dict) -> dict:
    template = (skill_dir / "assets" / "templates" / "article_shell.html").read_text(encoding="utf-8-sig")
    reference_entries = build_reference_entries(formatted.get("source_notes", []), formatted.get("reference_videos", []))
    resource_links = build_resource_links(formatted.get("source_notes", []), reference_entries)
    final_markdown = build_complete_markdown(
        formatted.get("body_markdown", ""),
        reference_entries,
        resource_links,
        skill_dir,
        brand_config,
    )
    final_html = render_template(
        template,
        {
            "title": html.escape(formatted.get("title", "")),
            "summary": html.escape(formatted.get("digest", "")),
            "body_html": markdown_to_html(final_markdown),
        },
    )
    return {
        **formatted,
        "body_markdown": final_markdown,
        "body_html": final_html,
        "brand_config": brand_config,
        "reference_entries": reference_entries,
        "resource_links": resource_links,
        "final_html": final_html,
    }

