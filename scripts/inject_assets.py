#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path

from utils.publishing import inject_blocks, load_brand_config

MARKDOWN_IMAGE_RE = re.compile(r'(!\[[^\]]*\]\()([^)]+)(\))')
HTML_IMAGE_SRC_RE = re.compile(r'(<img\b[^>]*\bsrc=")([^"]+)(")', re.IGNORECASE)
REMOTE_PREFIXES = ("http://", "https://", "data:")


class PreviewAssetLocalizer:
    def __init__(self, *, preview_dir: Path, skill_dir: Path) -> None:
        self.preview_dir = preview_dir
        self.skill_dir = skill_dir
        self.asset_dir = preview_dir / "preview-assets"
        self.asset_dir.mkdir(parents=True, exist_ok=True)
        self._copied: dict[str, str] = {}
        self._counter = 0

    @staticmethod
    def _normalize_src(value: str) -> str:
        return value.replace("\\", "/")

    def _is_remote_src(self, src: str) -> bool:
        normalized = src.strip().lower()
        return normalized.startswith(REMOTE_PREFIXES)

    def _resolve_existing_local_path(self, src: str) -> Path | None:
        normalized = self._normalize_src(src).strip()
        if not normalized or self._is_remote_src(normalized):
            return None

        candidate = Path(normalized)
        resolved_candidates: list[Path] = []
        if candidate.is_absolute():
            resolved_candidates.append(candidate)
        else:
            resolved_candidates.extend([
                self.skill_dir / candidate,
                self.preview_dir / candidate,
                Path.cwd() / candidate,
            ])

        for raw_path in resolved_candidates:
            try:
                existing_path = raw_path.resolve()
            except OSError:
                continue
            if existing_path.exists():
                return existing_path
        return None

    def localize(self, src: str) -> str:
        normalized = self._normalize_src(src).strip()
        if not normalized or self._is_remote_src(normalized):
            return normalized

        existing_path = self._resolve_existing_local_path(normalized)
        if existing_path is None:
            return normalized

        cache_key = str(existing_path).lower()
        cached = self._copied.get(cache_key)
        if cached:
            return cached

        self._counter += 1
        suffix = existing_path.suffix.lower() or ".bin"
        target_name = f"asset-{self._counter:03d}{suffix}"
        target_path = self.asset_dir / target_name
        shutil.copy2(existing_path, target_path)
        relative = self._normalize_src(target_path.relative_to(self.preview_dir).as_posix())
        self._copied[cache_key] = relative
        return relative

    def rewrite_markdown(self, markdown_text: str) -> str:
        def replace(match: re.Match[str]) -> str:
            localized = self.localize(match.group(2))
            return f"{match.group(1)}{localized}{match.group(3)}"

        return MARKDOWN_IMAGE_RE.sub(replace, markdown_text)

    def rewrite_html(self, html_text: str) -> str:
        def replace(match: re.Match[str]) -> str:
            localized = self.localize(match.group(2))
            return f"{match.group(1)}{localized}{match.group(3)}"

        return HTML_IMAGE_SRC_RE.sub(replace, html_text)


def derive_preview_markdown_path(output_path: Path) -> Path:
    if output_path.suffix.lower() == ".json":
        return output_path.with_name("article_preview.md")
    return output_path.with_name(f"{output_path.name}.md")


def derive_preview_html_path(output_path: Path) -> Path:
    if output_path.suffix.lower() == ".json":
        return output_path.with_name("article_preview.html")
    return output_path.with_name(f"{output_path.name}.html")


def rewrite_preview_paths(final_package: dict, *, output_dir: Path, skill_dir: Path) -> dict:
    rewritten = dict(final_package)
    localizer = PreviewAssetLocalizer(preview_dir=output_dir, skill_dir=skill_dir)

    body_markdown = rewritten.get("body_markdown") or ""
    body_html = rewritten.get("body_html") or ""
    final_html = rewritten.get("final_html") or ""

    rewritten["body_markdown"] = localizer.rewrite_html(localizer.rewrite_markdown(body_markdown))
    rewritten["body_html"] = localizer.rewrite_html(body_html)
    rewritten["final_html"] = localizer.rewrite_html(final_html)
    return rewritten


def main() -> None:
    parser = argparse.ArgumentParser(description="Inject fixed branding blocks into formatted HTML.")
    parser.add_argument("input", help="Path to formatted article JSON.")
    parser.add_argument("--output", required=True, help="Path to final article package JSON.")
    parser.add_argument("--brand-config", help="Optional config JSON path. Accepts either a dedicated brand config or a merged live config with a brand section.")
    args = parser.parse_args()

    formatted = json.loads(Path(args.input).read_text(encoding="utf-8-sig"))
    brand_config = load_brand_config(args.brand_config)
    skill_dir = Path(__file__).resolve().parent.parent

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    final_package = inject_blocks(formatted, skill_dir, brand_config)
    final_package = rewrite_preview_paths(final_package, output_dir=output_path.parent.resolve(), skill_dir=skill_dir)

    output_path.write_text(json.dumps(final_package, ensure_ascii=False, indent=2), encoding="utf-8")
    preview_markdown_path = derive_preview_markdown_path(output_path)
    preview_markdown = final_package.get("body_markdown") or ""
    preview_markdown_path.write_text(preview_markdown, encoding="utf-8")
    preview_html_path = derive_preview_html_path(output_path)
    preview_html = final_package.get("final_html") or final_package.get("body_html", "")
    preview_html_path.write_text(preview_html, encoding="utf-8")

    print(f"Wrote {output_path}")
    print(f"Wrote {preview_markdown_path}")
    print(f"Wrote {preview_html_path}")


if __name__ == "__main__":
    main()
