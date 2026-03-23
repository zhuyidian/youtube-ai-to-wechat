from __future__ import annotations


def clamp_candidate_cap(value: int, fallback: int = 20) -> int:
    if value <= 0:
        return fallback
    return min(value, 50)
