#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from pathlib import Path

from utils.article_builder import rewrite_wechat_article
from utils.llm_client import OpenAICompatibleClient, extract_json, load_llm_config
from utils.llm_writing import build_rewrite_prompts, enforce_source_bounded_markdown, normalize_text_list, soften_unverified_language


def run_llm(article: dict, config_path: str | None) -> dict:
    config = load_llm_config(config_path)
    client = OpenAICompatibleClient(config)
    system_prompt, user_prompt = build_rewrite_prompts(article)
    result = extract_json(client.chat(system_prompt, user_prompt))

    review_flags = normalize_text_list(result.get("review_flags", [])) or normalize_text_list(article.get("review_flags", []))
    body_markdown = enforce_source_bounded_markdown(
        result.get("body_markdown") or result.get("article_markdown") or article.get("body_markdown", ""),
        {
            **article,
            "review_flags": review_flags,
        },
    )

    title_candidates = article.get("title_candidates") or []
    selected_title = article.get("selected_title") or (title_candidates[0] if title_candidates else "")
    final_title = result.get("final_title") or result.get("title") or selected_title
    digest = result.get("digest") or result.get("summary") or ""
    cover_copy = result.get("cover_copy") or final_title

    return {
        "task": article.get("task", {}),
        "article_type": article.get("article_type"),
        "final_title": soften_unverified_language(final_title),
        "digest": soften_unverified_language(digest),
        "cover_copy": soften_unverified_language(cover_copy),
        "body_markdown": body_markdown,
        "source_notes": article.get("source_notes", []),
        "review_flags": review_flags,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Rewrite an article draft into WeChat-style markdown.")
    parser.add_argument("input", help="Path to article draft JSON.")
    parser.add_argument("--output", required=True, help="Path to rewritten article JSON.")
    parser.add_argument("--execute", action="store_true", help="Call a real LLM instead of local heuristics.")
    parser.add_argument("--config", help="Optional config JSON path. Accepts either a dedicated LLM config or a merged live config with an llm section.")
    args = parser.parse_args()

    article = json.loads(Path(args.input).read_text(encoding="utf-8-sig"))
    rewritten = run_llm(article, args.config) if args.execute else rewrite_wechat_article(article)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(rewritten, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
