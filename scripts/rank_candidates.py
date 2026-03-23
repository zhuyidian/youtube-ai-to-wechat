#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from utils.content_scorer import rank_candidates


def load_whitelist(path: str | None) -> set[str]:
    if not path:
        return set()
    whitelist_path = Path(path)
    if whitelist_path.suffix.lower() == ".json":
        values = json.loads(whitelist_path.read_text(encoding="utf-8"))
        return {str(value).strip().lower() for value in values if str(value).strip()}
    return {
        line.strip().lower()
        for line in whitelist_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Rank normalized YouTube candidates.")
    parser.add_argument("input", help="Path to search output JSON.")
    parser.add_argument("--output", required=True, help="Path to ranked output JSON.")
    parser.add_argument("--whitelist", help="Optional JSON or txt whitelist of channel titles.")
    args = parser.parse_args()

    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    whitelist = load_whitelist(args.whitelist)

    ranked = rank_candidates(payload.get("candidates", []), payload.get("task", {}), whitelist)
    max_selected = int(payload.get("task", {}).get("max_selected_videos", 3) or 3)

    output = {
        "task": payload.get("task", {}),
        "queries": payload.get("queries", []),
        "selected_candidates": ranked[:max_selected],
        "ranked_candidates": ranked,
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
