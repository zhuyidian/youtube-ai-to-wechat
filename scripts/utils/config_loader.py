from __future__ import annotations

import json
from pathlib import Path

DEFAULT_TASK = {
    "time_range": "7d",
    "language": ["zh", "en"],
    "article_type": "auto",
    "publish_mode": "draft_only",
    "max_candidates": 20,
    "max_selected_videos": 3,
    "cost_budget": "low",
}


def load_task(path: str) -> dict:
    payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    return {**DEFAULT_TASK, **payload}
