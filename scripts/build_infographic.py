#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from utils.media_planner import build_infographic_plan


def main() -> None:
    parser = argparse.ArgumentParser(description="Build an infographic plan from article content.")
    parser.add_argument("input", help="Path to final or formatted article JSON.")
    parser.add_argument("--output", required=True, help="Path to infographic plan JSON.")
    args = parser.parse_args()

    package = json.loads(Path(args.input).read_text(encoding="utf-8-sig"))
    plan = build_infographic_plan(package)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8-sig")
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()

