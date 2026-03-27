#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path

from utils.api_clients import WeChatOfficialAccountClient
from utils.media_planner import build_draft_payload, load_publish_config


SRC_RE = re.compile(r'src="([^"]+)"')


def resolve_env_with_aliases(primary_name: str | None, aliases: list[str]) -> str | None:
    names = [primary_name] if primary_name else []
    names.extend(alias for alias in aliases if alias not in names)

    for name in names:
        if not name:
            continue
        value = os.getenv(name)
        if value:
            return value
    return None


def resolve_wechat_client(config: dict) -> WeChatOfficialAccountClient:
    access_token = resolve_env_with_aliases(
        config.get("access_token_env", "WECHAT_ACCESS_TOKEN"),
        ["WXAccessToken"],
    )
    app_id = resolve_env_with_aliases(
        config.get("app_id_env", "WECHAT_APP_ID"),
        ["WXAppID"],
    )
    app_secret = resolve_env_with_aliases(
        config.get("app_secret_env", "WECHAT_APP_SECRET"),
        ["WXAppSecret"],
    )
    return WeChatOfficialAccountClient(
        base_url=config.get("base_url", "https://api.weixin.qq.com"),
        access_token=access_token,
        app_id=app_id,
        app_secret=app_secret,
    )


def upload_inline_images(client: WeChatOfficialAccountClient, html_text: str) -> tuple[str, list[dict]]:
    replacements: dict[str, str] = {}
    uploaded: list[dict] = []

    for src in SRC_RE.findall(html_text):
        if src.startswith("http://") or src.startswith("https://"):
            continue

        path = Path(src)
        if not path.exists() or not path.is_file():
            continue

        if src in replacements:
            continue

        response = client.upload_article_image(src)
        url = response.get("url")
        if not url:
            continue

        replacements[src] = url
        uploaded.append({"local_path": src, "url": url})

    for local_path, url in replacements.items():
        html_text = html_text.replace(f'src="{local_path}"', f'src="{url}"')

    return html_text, uploaded


def main() -> None:
    parser = argparse.ArgumentParser(description="Build or execute a WeChat draft payload from the final article package.")
    parser.add_argument("input", help="Path to final article package JSON.")
    parser.add_argument("--output", required=True, help="Path to draft payload JSON.")
    parser.add_argument("--image-package", help="Optional image package JSON path.")
    parser.add_argument("--infographic-plan", help="Optional infographic plan JSON path.")
    parser.add_argument("--publish-config", help="Optional config JSON path. Accepts either a dedicated publish config or a merged live config with a publish section.")
    parser.add_argument("--execute", action="store_true", help="Upload cover and create a real WeChat draft.")
    args = parser.parse_args()

    final_package = json.loads(Path(args.input).read_text(encoding="utf-8-sig"))
    image_package = json.loads(Path(args.image_package).read_text(encoding="utf-8-sig")) if args.image_package else None
    infographic_plan = json.loads(Path(args.infographic_plan).read_text(encoding="utf-8-sig")) if args.infographic_plan else None
    publish_config = load_publish_config(args.publish_config)
    uploaded_inline_images: list[dict] = []

    if args.execute:
        client = resolve_wechat_client(publish_config)
        cover_media_id = publish_config.get("cover_media_id", "")
        cover_image_path = (image_package or {}).get("cover_image_path")
        if cover_image_path:
            upload_result = client.upload_material(cover_image_path, media_type="thumb")
            cover_media_id = upload_result.get("media_id") or cover_media_id
        if not cover_media_id or cover_media_id == "TODO_UPLOAD_COVER":
            raise ValueError("No usable cover media_id. Generate and upload a cover or provide cover_media_id in publish config.")

        publish_config = {**publish_config, "cover_media_id": cover_media_id}
        rewritten_html, uploaded_inline_images = upload_inline_images(client, final_package.get("final_html") or final_package.get("body_html", ""))
        final_package = {**final_package, "final_html": rewritten_html}

    payload = build_draft_payload(final_package, image_package, infographic_plan, publish_config)
    if uploaded_inline_images:
        payload["uploaded_inline_images"] = uploaded_inline_images

    if args.execute:
        client = resolve_wechat_client(publish_config)
        response = client.add_draft(payload["wechat_api_payload"])
        payload["status"] = "draft_created"
        payload["wechat_response"] = response

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8-sig")
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
