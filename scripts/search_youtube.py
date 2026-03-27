#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable
from urllib.error import HTTPError

from utils.api_clients import YouTubeDataApiClient
from utils.config_loader import load_task


def parse_time_range(value: str | None) -> str | None:
    if not value:
        return None
    match = re.fullmatch(r"(\d+)([dhw])", value.strip().lower())
    if not match:
        return None
    amount = int(match.group(1))
    unit = match.group(2)
    if unit == "d":
        delta = timedelta(days=amount)
    elif unit == "h":
        delta = timedelta(hours=amount)
    else:
        delta = timedelta(weeks=amount)
    return (datetime.now(timezone.utc) - delta).isoformat().replace("+00:00", "Z")


def dedupe(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = value.strip()
        if not normalized:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(normalized)
    return result


def chunked(values: list[str], size: int) -> list[list[str]]:
    if size <= 0:
        raise ValueError("chunk size must be > 0")
    return [values[index : index + size] for index in range(0, len(values), size)]


def build_queries(task: dict) -> list[str]:
    base_queries: list[str] = []
    if task.get("topic"):
        base_queries.append(task["topic"])
    base_queries.extend(task.get("keywords", []))

    expanded: list[str] = []
    for query in base_queries:
        lowered = query.lower()
        expanded.append(query)
        if "ai" not in lowered and "娴滃搫浼愰弲楦垮厴" not in query:
            expanded.append(f"{query} AI")
    return dedupe(expanded)[:6]


def parse_duration_to_seconds(value: str | None) -> int:
    if not value:
        return 0
    match = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", value)
    if not match:
        return 0
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    return hours * 3600 + minutes * 60 + seconds


def pick_thumbnail(snippet: dict) -> str | None:
    thumbnails = snippet.get("thumbnails", {})
    for key in ("maxres", "high", "medium", "default"):
        if key in thumbnails and thumbnails[key].get("url"):
            return thumbnails[key]["url"]
    return None


def collect_ids(search_items: list[tuple[str, dict]], field: str) -> list[str]:
    values: list[str] = []
    for _, item in search_items:
        if field == "videoId":
            raw = item.get("id", {}).get("videoId", "")
        else:
            raw = item.get("snippet", {}).get(field, "")
        if isinstance(raw, str):
            normalized = raw.strip()
            if normalized:
                values.append(normalized)
    return dedupe(values)


def load_videos_by_id(client: YouTubeDataApiClient, video_ids: list[str]) -> dict[str, dict]:
    videos_by_id: dict[str, dict] = {}
    for batch in chunked(video_ids, 20):
        try:
            response = client.get_videos(batch)
        except HTTPError as exc:
            print(
                f"Warning: get_videos batch failed for {len(batch)} ids ({exc}); retrying individually.",
                file=sys.stderr,
            )
            response = {"items": []}
            for video_id in batch:
                try:
                    single = client.get_videos([video_id])
                except HTTPError as single_exc:
                    print(f"Warning: skipped video metadata for {video_id} ({single_exc})", file=sys.stderr)
                    continue
                response["items"].extend(single.get("items", []))
        for item in response.get("items", []):
            item_id = item.get("id")
            if item_id:
                videos_by_id[item_id] = item
    return videos_by_id


def load_channels_by_id(client: YouTubeDataApiClient, channel_ids: list[str]) -> dict[str, dict]:
    channels_by_id: dict[str, dict] = {}
    for batch in chunked(channel_ids, 20):
        try:
            response = client.get_channels(batch)
        except HTTPError as exc:
            print(
                f"Warning: get_channels batch failed for {len(batch)} ids ({exc}); retrying individually.",
                file=sys.stderr,
            )
            response = {"items": []}
            for channel_id in batch:
                try:
                    single = client.get_channels([channel_id])
                except HTTPError as single_exc:
                    print(f"Warning: skipped channel metadata for {channel_id} ({single_exc})", file=sys.stderr)
                    continue
                response["items"].extend(single.get("items", []))
        for item in response.get("items", []):
            item_id = item.get("id")
            if item_id:
                channels_by_id[item_id] = item
    return channels_by_id


def normalize_candidate(search_item: dict, video: dict, channel: dict, source_query: str) -> dict:
    snippet = search_item.get("snippet", {})
    video_snippet = video.get("snippet", {})
    statistics = video.get("statistics", {})
    content_details = video.get("contentDetails", {})
    channel_stats = channel.get("statistics", {})

    video_id = search_item.get("id", {}).get("videoId") or video.get("id")
    channel_id = snippet.get("channelId") or video_snippet.get("channelId")

    return {
        "video_id": video_id,
        "url": f"https://www.youtube.com/watch?v={video_id}",
        "title": snippet.get("title") or video_snippet.get("title") or "",
        "description": snippet.get("description") or video_snippet.get("description") or "",
        "published_at": snippet.get("publishedAt") or video_snippet.get("publishedAt"),
        "source_query": source_query,
        "channel_id": channel_id,
        "channel_title": snippet.get("channelTitle") or video_snippet.get("channelTitle") or "",
        "channel_subscriber_count": int(channel_stats.get("subscriberCount", 0) or 0),
        "thumbnail_url": pick_thumbnail(snippet) or pick_thumbnail(video_snippet),
        "duration_iso8601": content_details.get("duration"),
        "duration_seconds": parse_duration_to_seconds(content_details.get("duration")),
        "view_count": int(statistics.get("viewCount", 0) or 0),
        "like_count": int(statistics.get("likeCount", 0) or 0),
        "comment_count": int(statistics.get("commentCount", 0) or 0),
        "default_audio_language": video_snippet.get("defaultAudioLanguage"),
        "default_language": video_snippet.get("defaultLanguage"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Search YouTube and normalize candidate videos.")
    parser.add_argument("task", help="Path to task JSON.")
    parser.add_argument("--output", required=True, help="Path to output JSON.")
    parser.add_argument("--per-query", type=int, default=8, help="Max results to fetch per query.")
    parser.add_argument("--fixtures-dir", help="Offline fixture directory with search/videos/channels JSON files.")
    parser.add_argument("--relevance-language", default="en", help="YouTube relevanceLanguage value.")
    parser.add_argument("--region-code", default="US", help="YouTube regionCode value.")
    args = parser.parse_args()

    task = load_task(args.task)
    queries = build_queries(task)
    published_after = parse_time_range(task.get("time_range"))

    client = YouTubeDataApiClient(fixtures_dir=args.fixtures_dir)

    search_items: list[tuple[str, dict]] = []
    seen_video_ids: set[str] = set()
    for query in queries:
        response = client.search_videos(
            query,
            published_after=published_after,
            max_results=args.per_query,
            relevance_language=args.relevance_language,
            region_code=args.region_code,
        )
        for item in response.get("items", []):
            video_id = item.get("id", {}).get("videoId")
            if not video_id or video_id in seen_video_ids:
                continue
            seen_video_ids.add(video_id)
            search_items.append((query, item))

    videos_by_id = load_videos_by_id(client, collect_ids(search_items, "videoId"))
    channels_by_id = load_channels_by_id(client, collect_ids(search_items, "channelId"))

    candidates = []
    for source_query, search_item in search_items:
        video_id = search_item.get("id", {}).get("videoId")
        video = videos_by_id.get(video_id, {})
        channel_id = search_item.get("snippet", {}).get("channelId")
        channel = channels_by_id.get(channel_id, {})
        candidates.append(normalize_candidate(search_item, video, channel, source_query))

    payload = {
        "task": task,
        "queries": queries,
        "candidate_count": len(candidates),
        "candidates": candidates,
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
