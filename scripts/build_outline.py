#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from utils.article_builder import build_outline_payload, choose_primary_item
from utils.llm_client import OpenAICompatibleClient, extract_json, load_llm_config
from utils.llm_writing import build_outline_prompts


def run_llm(source_pack: dict, config_path: str | None) -> dict:
    config = load_llm_config(config_path)
    client = OpenAICompatibleClient(config)
    system_prompt, user_prompt = build_outline_prompts(source_pack)
    result = extract_json(client.chat(system_prompt, user_prompt))
    return {
        "task": source_pack.get("task", {}),
        "article_type": result["article_type"],
        "title_candidates": result["title_candidates"],
        "selected_title": result["selected_title"],
        "summary_angle": result["summary_angle"],
        "primary_item": choose_primary_item(source_pack.get("research_items", [])),
        "research_items": source_pack.get("research_items", []),
        "sections": result["sections"],
        "open_questions": result["open_questions"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build an outline from the source pack.")
    parser.add_argument("input", help="Path to source pack JSON.")
    parser.add_argument("--output", required=True, help="Path to outline JSON.")
    parser.add_argument("--execute", action="store_true", help="Call a real LLM instead of local heuristics.")
    parser.add_argument("--config", help="Optional config JSON path. Accepts either a dedicated LLM config or a merged live config with an llm section.")
    args = parser.parse_args()

    payload = json.loads(Path(args.input).read_text(encoding="utf-8-sig"))
    outline = run_llm(payload, args.config) if args.execute else build_outline_payload(payload)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(outline, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()

