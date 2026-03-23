from __future__ import annotations

import json
from pathlib import Path


IMAGE_STYLE_TEMPLATE = (
    "Create a high-quality editorial illustration on textured off-white paper. "
    "Use abstract network structures, symbolic shapes, and clean composition. "
    "Do not include text, labels, UI screenshots, phone frames, or readable glyphs. "
    "Keep the image concept-focused, visually clean, and suitable for WeChat articles."
)


def _clean_text(value: object, fallback: str) -> str:
    text = str(value or "").strip()
    return text or fallback


def _compact_digest(article: dict) -> str:
    digest = _clean_text(article.get("digest"), "")
    return digest[:120] if digest else ""


def _build_image_prompt(*, usage: str, subject: str, aspect_ratio: str, article: dict) -> str:
    digest = _compact_digest(article)
    lines = [
        IMAGE_STYLE_TEMPLATE,
        f"Usage: {usage}.",
        f"Subject: {subject}.",
    ]
    if digest:
        lines.append(f"Article digest: {digest}.")
    lines.extend(
        [
            "Express the topic through composition, lighting, structure, and symbolic elements only.",
            "Avoid screenshots, poster layouts, and any visible text.",
            f"Target aspect ratio: {aspect_ratio}.",
        ]
    )
    return "\n".join(lines)


def load_publish_config(path: str | None) -> dict:
    defaults = {
        "author": "AI Observer",
        "content_source_url": "",
        "need_open_comment": 0,
        "only_fans_can_comment": 0,
        "publish_mode": "draft_only",
        "cover_media_id": "TODO_UPLOAD_COVER",
        "base_url": "https://api.weixin.qq.com",
        "access_token_env": "WECHAT_ACCESS_TOKEN",
        "app_id_env": "WECHAT_APP_ID",
        "app_secret_env": "WECHAT_APP_SECRET",
    }
    if not path:
        return defaults
    payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    section = payload.get("publish", payload)
    return {**defaults, **section}


def build_image_requests(article: dict) -> dict:
    headings = [line[3:].strip() for line in str(article.get("body_markdown", "")).splitlines() if line.startswith("## ")]
    inline_requests = []
    article_title = _clean_text(article.get("final_title") or article.get("selected_title"), "AI article")
    for index, heading in enumerate(headings[:3], 1):
        subject = f"{article_title}, section: {heading}"
        inline_requests.append({
            "asset_id": f"inline-{index:03d}",
            "type": "inline",
            "section_heading": heading,
            "search_query": f"{article_title} {heading}",
            "prompt": _build_image_prompt(
                usage="WeChat inline illustration",
                subject=subject,
                aspect_ratio="4:5",
                article=article,
            ),
            "aspect_ratio": "4:5",
        })
    return {
        "cover_request": {
            "asset_id": "cover-001",
            "type": "cover",
            "cover_copy": article.get("cover_copy") or article_title,
            "search_query": article_title,
            "prompt": _build_image_prompt(
                usage="WeChat cover image",
                subject=article_title,
                aspect_ratio="2.35:1",
                article=article,
            ),
            "aspect_ratio": "2.35:1",
        },
        "inline_requests": inline_requests,
        "infographic_request": {
            "asset_id": "info-001",
            "type": "infographic",
            "concept": article_title,
            "search_query": f"{article_title} infographic",
            "prompt": _build_image_prompt(
                usage="WeChat infographic hero image",
                subject=f"{article_title}, emphasize structure and relationships",
                aspect_ratio="4:5",
                article=article,
            ),
            "aspect_ratio": "4:5",
        },
    }


def build_infographic_plan(article: dict) -> dict:
    return {
        "asset_id": "info-001",
        "concept": article.get("title") or article.get("final_title") or article.get("selected_title") or "AI article",
        "status": "planned",
    }


def build_draft_payload(final_package: dict, image_package: dict | None, infographic_plan: dict | None, publish_config: dict) -> dict:
    title = final_package.get("title") or final_package.get("final_title") or "Untitled"
    digest = final_package.get("digest") or ""
    html = final_package.get("final_html") or final_package.get("body_html") or ""
    thumb_media_id = publish_config.get("cover_media_id", "TODO_UPLOAD_COVER")
    payload = {
        "articles": [{
            "title": title,
            "author": publish_config.get("author", ""),
            "digest": digest,
            "content": html,
            "content_source_url": publish_config.get("content_source_url", ""),
            "thumb_media_id": thumb_media_id,
            "need_open_comment": publish_config.get("need_open_comment", 0),
            "only_fans_can_comment": publish_config.get("only_fans_can_comment", 0),
        }]
    }
    return {
        "status": "draft_payload_built",
        "title": title,
        "digest": digest,
        "wechat_api_payload": payload,
        "image_package": image_package,
        "infographic_plan": infographic_plan,
        "publish_config": publish_config,
    }
