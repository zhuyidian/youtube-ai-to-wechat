#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from pathlib import Path

from utils.article_builder import render_information_article
from utils.llm_client import OpenAICompatibleClient, extract_json, load_llm_config
from utils.llm_writing import build_article_prompts, enforce_source_bounded_markdown, normalize_text_list


def run_llm(outline: dict, config_path: str | None) -> dict:
    config = load_llm_config(config_path)
    client = OpenAICompatibleClient(config)
    system_prompt, user_prompt = build_article_prompts(outline)
    result = extract_json(client.chat(system_prompt, user_prompt))

    source_notes = [
        {
            "video_id": item.get("video_id"),
            "title": item.get("title"),
            "url": item.get("url"),
            "channel_id": item.get("channel_id"),
            "channel_title": item.get("channel_title"),
            "published_at": item.get("published_at"),
            "sources": item.get("sources", []),
        }
        for item in outline.get("research_items", [])
    ]

    review_flags = normalize_text_list(result.get("review_flags", [])) or normalize_text_list(outline.get("open_questions", []))
    body_markdown = enforce_source_bounded_markdown(
        result.get("body_markdown") or result.get("article_markdown") or "",
        {
            **outline,
            "source_notes": source_notes,
            "review_flags": review_flags,
        },
    )

    return {
        "task": outline.get("task", {}),
        "article_type": outline.get("article_type"),
        "title_candidates": result.get("title_candidates") or outline.get("title_candidates", []),
        "selected_title": result.get("selected_title") or outline.get("selected_title"),
        "body_markdown": body_markdown,
        "source_notes": source_notes,
        "review_flags": review_flags,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Write an information-pass article from an outline.")
    parser.add_argument("input", help="Path to outline JSON.")
    parser.add_argument("--output", required=True, help="Path to article draft JSON.")
    parser.add_argument("--execute", action="store_true", help="Call a real LLM instead of local heuristics.")
    parser.add_argument("--config", help="Optional config JSON path. Accepts either a dedicated LLM config or a merged live config with an llm section.")
    args = parser.parse_args()

    outline = json.loads(Path(args.input).read_text(encoding="utf-8-sig"))
    article = run_llm(outline, args.config) if args.execute else render_information_article(outline)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(article, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
