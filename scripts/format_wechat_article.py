#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from utils.publishing import build_formatted_article


def main() -> None:
    parser = argparse.ArgumentParser(description="Format a headline bundle into WeChat HTML.")
    parser.add_argument("input", help="Path to headline bundle JSON.")
    parser.add_argument("--output", required=True, help="Path to formatted article JSON.")
    parser.add_argument("--image-package", help="Optional image package JSON path.")
    args = parser.parse_args()

    bundle = json.loads(Path(args.input).read_text(encoding="utf-8-sig"))
    image_package = json.loads(Path(args.image_package).read_text(encoding="utf-8-sig")) if args.image_package else None
    skill_dir = Path(__file__).resolve().parent.parent
    formatted = build_formatted_article(bundle, skill_dir, image_package=image_package)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(formatted, ensure_ascii=False, indent=2), encoding="utf-8-sig")
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()

