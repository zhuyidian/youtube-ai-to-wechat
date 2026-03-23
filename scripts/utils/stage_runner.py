from __future__ import annotations

import json
from pathlib import Path


def run_stub(stage_name: str, description: str) -> None:
    payload = {
        "stage": stage_name,
        "description": description,
        "status": "stubbed",
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
