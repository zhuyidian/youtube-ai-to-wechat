from __future__ import annotations

import json
import re
from typing import Any


REMOVED_TAIL_SECTIONS = {"信息来源", "公众号信息", "参考视频清单", "参考资料"}
REMOVED_BOLD_HEADINGS = {"**信息来源**", "**公众号信息**", "**参考视频清单**", "**参考资料**"}


def normalize_text_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        items = [value]
    elif isinstance(value, list):
        items = []
        for item in value:
            if isinstance(item, str):
                items.append(item)
            elif isinstance(item, dict):
                text = item.get("text") or item.get("label") or item.get("title")
                if text:
                    items.append(str(text))
            elif item is not None:
                items.append(str(item))
    else:
        items = [str(value)]

    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        text = re.sub(r"\s+", " ", item).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def soften_unverified_language(text: str) -> str:
    softened = text
    replacements = {
        "已经证明": "目前更像是",
        "可以确定": "目前可以初步判断",
        "毫无疑问": "较大概率",
        "一定会": "很可能会",
        "必然会": "可能会",
    }
    for source, target in replacements.items():
        softened = softened.replace(source, target)
    return softened.strip()


def _strip_removed_sections(markdown_text: str) -> str:
    result: list[str] = []
    skip_section = False

    for raw_line in markdown_text.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()

        if stripped.startswith("## ") or stripped.startswith("### "):
            heading = stripped.split(" ", 1)[1].strip()
            skip_section = heading in REMOVED_TAIL_SECTIONS
            if skip_section:
                continue
        elif stripped in REMOVED_BOLD_HEADINGS:
            skip_section = True
            continue
        elif stripped == "---" and skip_section:
            skip_section = False
            continue

        if skip_section:
            continue
        result.append(line)

    return "\n".join(result).strip()


def enforce_source_bounded_markdown(body_markdown: str, article: dict) -> str:
    body = _strip_removed_sections(body_markdown.strip())
    if not body:
        return body

    review_flags = normalize_text_list(article.get("review_flags"))
    if not review_flags:
        return body

    review_section = "## 需要继续核验\n" + "\n".join(f"- {item}" for item in review_flags)
    return body + "\n\n" + review_section + "\n"


def _dump_payload(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)


def build_outline_prompts(source_pack: dict) -> tuple[str, str]:
    system_prompt = (
        "You are an editor planning a Chinese WeChat article from YouTube research. "
        "Be factual, source-bounded, and return JSON only."
    )
    user_prompt = (
        "Based on the following source pack, produce JSON with fields: "
        "article_type, title_candidates, selected_title, summary_angle, sections, open_questions. "
        "Each section must include heading, purpose, bullets, source_video_ids. "
        "Keep the angle practical and avoid unsupported claims.\n\n"
        f"{_dump_payload(source_pack)}"
    )
    return system_prompt, user_prompt


def build_article_prompts(outline: dict) -> tuple[str, str]:
    system_prompt = (
        "You write concise Chinese WeChat article drafts grounded in provided sources. "
        "Return JSON only."
    )
    user_prompt = (
        "Write the article from this outline. Return JSON with fields: body_markdown, review_flags. "
        "The markdown should have a strong opening, section headings, practical analysis, and cautious wording. "
        "Do not include a public-account profile section or a source list section.\n\n"
        f"{_dump_payload(outline)}"
    )
    return system_prompt, user_prompt


def build_rewrite_prompts(article: dict) -> tuple[str, str]:
    system_prompt = (
        "You are polishing a Chinese WeChat article for readability and publishing. "
        "Preserve facts, keep claims cautious, and return JSON only."
    )
    user_prompt = (
        "Rewrite this article into cleaner WeChat style. Return JSON with fields: "
        "final_title, digest, cover_copy, body_markdown, review_flags. "
        "Do not invent facts beyond the provided article. "
        "Do not add a public-account profile section or a source list section.\n\n"
        f"{_dump_payload(article)}"
    )
    return system_prompt, user_prompt
