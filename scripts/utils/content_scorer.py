from __future__ import annotations

TOPIC_HINTS = ("ai", "agent", "model", "openai", "gpt", "gemini", "anthropic", "claude")


def _score_topic_fit(candidate: dict, topic: str) -> int:
    title = str(candidate.get("title", "")).lower()
    topic_lower = topic.lower().strip()
    score = 0
    if topic_lower and topic_lower in title:
        score += 5
    score += sum(1 for hint in TOPIC_HINTS if hint in title)
    return min(score, 10)


def _score_channel_quality(candidate: dict) -> int:
    subscribers = int(candidate.get("channel_subscriber_count") or 0)
    if subscribers >= 1_000_000:
        return 10
    if subscribers >= 100_000:
        return 8
    if subscribers >= 10_000:
        return 6
    if subscribers >= 1_000:
        return 4
    return 2


def rank_candidates(candidates: list[dict], task: dict, whitelist: set[str] | None = None) -> list[dict]:
    whitelist = whitelist or set()
    topic = str(task.get("topic", ""))
    ranked = []
    for index, candidate in enumerate(candidates, 1):
        topic_fit = _score_topic_fit(candidate, topic)
        channel_quality = _score_channel_quality(candidate)
        whitelist_bonus = 3 if str(candidate.get("channel_title", "")).strip().lower() in whitelist else 0
        information_density = 2 if int(candidate.get("duration_seconds") or 0) >= 300 else 1
        total = topic_fit + channel_quality + whitelist_bonus + information_density
        notes = []
        if topic_fit < 4:
            notes.append("weak-topic-fit")
        if channel_quality < 4:
            notes.append("low-channel-confidence")
        ranked.append({
            **candidate,
            "rank": index,
            "score_total": total,
            "score_breakdown": {
                "topic_fit": topic_fit,
                "channel_quality": channel_quality,
                "whitelist_bonus": whitelist_bonus,
                "information_density": information_density,
            },
            "notes": notes,
        })
    ranked.sort(key=lambda item: item.get("score_total", 0), reverse=True)
    for idx, item in enumerate(ranked, 1):
        item["rank"] = idx
    return ranked
