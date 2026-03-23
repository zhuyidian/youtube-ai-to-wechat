#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from pathlib import Path


def build_transcript_text(candidate: dict) -> str:
    parts: list[str] = []
    title = str(candidate.get("title") or "").strip()
    description = str(candidate.get("description") or "").strip()
    if title:
        parts.append(title)
    if description:
        parts.append(description)
    return "\n\n".join(parts).strip()


def normalize_entry(candidate: dict) -> dict:
    transcript_text = build_transcript_text(candidate)
    return {
        "video_id": candidate.get("video_id"),
        "title": candidate.get("title"),
        "url": candidate.get("url"),
        "channel_id": candidate.get("channel_id"),
        "channel_title": candidate.get("channel_title"),
        "published_at": candidate.get("published_at"),
        "status": "metadata_only",
        "transcript_text": transcript_text,
        "transcript_segments": [],
        "source_query": candidate.get("source_query"),
        "score_total": candidate.get("score_total"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch or synthesize transcript data for ranked candidates.")
    parser.add_argument("input", help="Path to ranked candidates JSON.")
    parser.add_argument("--output", required=True, help="Path to transcript pack JSON.")
    parser.add_argument("--fixtures-dir", help="Optional fixtures directory. Currently unused by metadata fallback.")
    args = parser.parse_args()

    payload = json.loads(Path(args.input).read_text(encoding="utf-8-sig"))
    selected_candidates = payload.get("selected_candidates", [])
    transcript_entries = [normalize_entry(candidate) for candidate in selected_candidates]

    output = {
        "task": payload.get("task", {}),
        "queries": payload.get("queries", []),
        "transcript_mode": "metadata_fallback",
        "transcript_entries": transcript_entries,
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8-sig")
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
