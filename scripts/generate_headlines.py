#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from utils.publishing import build_headline_bundle


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate title, digest, and cover copy bundle.")
    parser.add_argument("input", help="Path to rewritten article JSON.")
    parser.add_argument("--output", required=True, help="Path to headline bundle JSON.")
    args = parser.parse_args()

    article = json.loads(Path(args.input).read_text(encoding="utf-8-sig"))
    bundle = build_headline_bundle(article)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()

