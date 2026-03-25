#!/usr/bin/env python3

from __future__ import annotations



import argparse

import json

import re

from pathlib import Path

from typing import Iterable



ENTITY_SOURCES = {

    "wechat": [

        "https://mp.weixin.qq.com",

        "https://developers.weixin.qq.com/doc/",

        "https://open.weixin.qq.com",

    ],

    "tencent": [

        "https://www.tencent.com/zh-cn/articles/index.html?type=all",

        "https://cloud.tencent.com/developer",

        "https://developers.weixin.qq.com/doc/",

    ],

    "n8n": [

        "https://n8n.io",

        "https://docs.n8n.io",

        "https://blog.n8n.io",

    ],

    "openai": [

        "https://openai.com/blog",

        "https://platform.openai.com/docs",

        "https://github.com/openai",

    ],

    "google": [

        "https://blog.google/technology/ai",

        "https://deepmind.google/discover/blog",

        "https://ai.google.dev",

    ],

    "gemini": [

        "https://blog.google/technology/ai",

        "https://deepmind.google/discover/blog",

        "https://ai.google.dev/gemini-api/docs",

    ],

    "anthropic": [

        "https://www.anthropic.com/news",

        "https://docs.anthropic.com",

    ],

    "claude": [

        "https://www.anthropic.com/news",

        "https://docs.anthropic.com",

    ],

    "meta": [

        "https://ai.meta.com/blog",

        "https://engineering.fb.com",

    ],

    "llama": [

        "https://ai.meta.com/blog",

        "https://huggingface.co/meta-llama",

    ],

    "microsoft": [

        "https://blogs.microsoft.com/blog/tag/ai",

        "https://learn.microsoft.com/azure/ai-services",

    ],

    "nvidia": [

        "https://blogs.nvidia.com",

        "https://developer.nvidia.com/blog",

    ],

}

ENTITY_ALIASES = {

    "wechat": ["wechat", "weixin", "微信", "公众号", "视频号", "小程序", "企业微信"],

    "tencent": ["tencent", "腾讯", "騰訊", "wxg", "wechat team"],

    "n8n": ["n8n"],

    "openai": ["openai"],

    "google": ["google", "谷歌"],

    "gemini": ["gemini"],

    "anthropic": ["anthropic"],

    "claude": ["claude"],

    "meta": ["meta"],

    "llama": ["llama"],

    "microsoft": ["microsoft", "微软", "azure"],

    "nvidia": ["nvidia", "英伟达"],

}

CLAIM_HINTS = ("launch", "release", "released", "new", "benchmark", "price", "agent", "model", "available", "support", "tool", "api")

SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
URL_RE = re.compile(r"https?://[^\s)>\]}]+", re.IGNORECASE)





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





def load_fixtures(fixtures_dir: str | None) -> dict:

    if not fixtures_dir:

        return {}

    path = Path(fixtures_dir) / "research.json"

    if not path.exists():

        return {}

    return json.loads(path.read_text(encoding="utf-8-sig"))





def detect_entities(text: str) -> list[str]:

    lowered = text.lower()

    entities: list[str] = []

    for entity, aliases in ENTITY_ALIASES.items():

        if any(alias.lower() in lowered for alias in aliases):

            entities.append(entity)

    return dedupe(entities)


def extract_urls(text: str) -> list[str]:

    matches: list[str] = []

    for raw_url in URL_RE.findall(text):

        normalized = raw_url.rstrip('.,;:!?)]}\"\'')

        if not normalized:

            continue

        matches.append(normalized)

    return dedupe(matches)



def extract_claims(text: str) -> list[str]:

    claims: list[str] = []

    for sentence in SENTENCE_SPLIT_RE.split(text):

        stripped = sentence.strip()

        if not stripped:

            continue

        lowered = stripped.lower()

        if any(hint in lowered for hint in CLAIM_HINTS) or any(ch.isdigit() for ch in stripped):

            claims.append(stripped)

    return claims[:5]





def build_search_queries(task: dict, candidate: dict, entities: list[str]) -> list[str]:

    queries = []

    if task.get("topic"):

        queries.append(task["topic"])

    queries.extend(task.get("keywords", []))

    queries.append(candidate.get("title", ""))

    for entity in entities:

        queries.append(f"{entity} official blog")

        queries.append(f"{entity} docs")

        queries.append(f"{entity} release notes")

    return dedupe(queries)





def dedupe_sources(items: list[dict]) -> list[dict]:

    seen_urls: set[str] = set()

    result: list[dict] = []

    for item in items:

        url = str(item.get("url") or "").strip()

        if not url:

            continue

        key = url.lower()

        if key in seen_urls:

            continue

        seen_urls.add(key)

        result.append(item)

    return result



def build_sources(transcript_text: str, entities: list[str], fixture_sources: list[dict] | None) -> tuple[str, list[dict]]:

    if fixture_sources:

        return "fixture", fixture_sources



    extracted_links = [

        {

            "type": "description_link",

            "url": url,

        }

        for url in extract_urls(transcript_text)

    ]



    generated = []

    for entity in entities:

        for url in ENTITY_SOURCES.get(entity, []):

            generated.append({

                "type": "official_candidate",

                "entity": entity,

                "url": url,

            })



    source_mode = "heuristic_description_links" if extracted_links else "heuristic"

    return (source_mode, dedupe_sources([*extracted_links, *generated]))



def build_research_item(task: dict, transcript_entry: dict, fixtures: dict) -> dict:

    entity_text = " ".join(

        [

            task.get("topic", ""),

            " ".join(task.get("keywords", [])),

            transcript_entry.get("title", ""),

            transcript_entry.get("transcript_text", ""),

        ]

    )
    claim_text = transcript_entry.get("transcript_text", "") or transcript_entry.get("title", "")

    entities = detect_entities(entity_text)

    claims = extract_claims(claim_text)

    fixture = fixtures.get(transcript_entry.get("video_id"), {})

    source_mode, sources = build_sources(transcript_entry.get("transcript_text", ""), entities, fixture.get("sources"))



    return {

        "video_id": transcript_entry.get("video_id"),

        "title": transcript_entry.get("title"),

        "url": transcript_entry.get("url"),

        "channel_id": transcript_entry.get("channel_id"),

        "channel_title": transcript_entry.get("channel_title"),

        "published_at": transcript_entry.get("published_at"),

        "transcript_status": transcript_entry.get("status"),

        "entities": entities,

        "claims_to_verify": claims,

        "search_queries": build_search_queries(task, transcript_entry, entities),

        "sources": sources,

        "source_mode": source_mode,

        "article_angle_hint": fixture.get("article_angle_hint") or f"Explain what changed in '{transcript_entry.get('title', '')}' and why it matters to AI readers.",

    }





def main() -> None:

    parser = argparse.ArgumentParser(description="Build a supplemental research pack from transcript data.")

    parser.add_argument("input", help="Path to transcript pack JSON.")

    parser.add_argument("--output", required=True, help="Path to output research JSON.")

    parser.add_argument("--fixtures-dir", help="Offline fixture directory containing research.json.")

    args = parser.parse_args()



    payload = json.loads(Path(args.input).read_text(encoding="utf-8-sig"))

    fixtures = load_fixtures(args.fixtures_dir)



    research_items = [

        build_research_item(payload.get("task", {}), transcript_entry, fixtures)

        for transcript_entry in payload.get("transcript_entries", [])

    ]



    output = {

        "task": payload.get("task", {}),

        "queries": payload.get("queries", []),

        "research_items": research_items,

        "unresolved_claims_count": sum(len(item.get("claims_to_verify", [])) for item in research_items),

    }



    output_path = Path(args.output)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8-sig")

    print(f"Wrote {output_path}")





if __name__ == "__main__":

    main()





