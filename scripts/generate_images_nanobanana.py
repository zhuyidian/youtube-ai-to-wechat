#!/usr/bin/env python3

from __future__ import annotations

import argparse
import html
import io
import json
import mimetypes
import os
import re
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin, urlparse
from urllib.request import Request, urlopen

from PIL import Image

from utils.api_clients import HttpError, JsonHttpClient, NanobananaClient
from utils.llm_client import OpenAICompatibleClient, extract_json, load_llm_config
from utils.media_planner import build_image_requests

IMAGE_REVIEW_SYSTEM_PROMPT = """You are a strict QA reviewer for generated editorial images used in Chinese WeChat articles.

Your job is to reject any image that contains visible text, letters, numbers, labels, captions, watermarks, pseudo-text, corrupted glyphs, or UI-like copy.

The required standard is text-free imagery.

Pass only when the image is visually clean and essentially text-free.

Return JSON only."""

TEXT_FREE_RULES = [
    "Hard rule: no text in image.",
    "Do not render Chinese, English, letters, numbers, labels, captions, watermarks, logos with text, pseudo-text, or garbled glyphs.",
    "Use icons, arrows, blocks, charts, shapes, and layout only; never draw prompt words as image text.",
]

MAX_MINIMAX_PROMPT_LENGTH = 1450
DEFAULT_USER_AGENT = "Mozilla/5.0 (compatible; youtube-ai-to-wechat/1.0; +https://openai.com)"
META_IMAGE_PATTERNS = [
    re.compile(r'<meta[^>]+property=["\']og:image(?::secure_url)?["\'][^>]+content=["\']([^"\']+)["\']', re.IGNORECASE),
    re.compile(r'<meta[^>]+name=["\']twitter:image(?::src)?["\'][^>]+content=["\']([^"\']+)["\']', re.IGNORECASE),
    re.compile(r'<link[^>]+rel=["\']image_src["\'][^>]+href=["\']([^"\']+)["\']', re.IGNORECASE),
]
HTML_IMAGE_RE = re.compile(r'<img[^>]+src=["\']([^"\']+)["\']', re.IGNORECASE)
BAD_IMAGE_HINTS = ("logo", "icon", "avatar", "favicon", "sprite", "badge")
YOUTUBE_HINTS = ("youtube.com", "youtu.be")
RELEVANCE_STOP_WORDS = {"the", "and", "for", "with", "from", "into", "over", "this", "that", "your", "what", "when", "where", "why", "how", "article", "wechat", "image", "images", "cover", "inline", "section", "trend", "trends", "guide", "practical"}
SHORT_KEEP_TOKENS = {"ai", "ml", "llm", "api", "gpt"}
ENTITY_TERM_WEIGHTS = {"openai": 4, "anthropic": 4, "google": 4, "gemini": 4, "claude": 4, "microsoft": 4, "meta": 4, "llama": 4, "nvidia": 4}
TYPE_PREFERRED_WEIGHTS = {
    "cover": {"agent": 8, "agents": 8, "architecture": 7, "workflow": 7, "overview": 7, "diagram": 7, "framework": 5, "system": 4},
    "inline": {"agent": 6, "agents": 6, "architecture": 5, "workflow": 5, "overview": 5, "diagram": 5, "tool": 4, "tools": 4, "api": 4, "automation": 4, "system": 3},
    "infographic": {"architecture": 10, "workflow": 10, "overview": 10, "diagram": 10, "framework": 7, "system": 7, "flow": 6, "network": 5},
}
NEGATIVE_TERM_WEIGHTS = {
    "visit": 24,
    "representatives": 24,
    "commission": 22,
    "meeting": 18,
    "parliament": 18,
    "speech": 14,
    "portrait": 14,
    "mobile": 20,
    "screenshot": 22,
    "app": 8,
    "church": 26,
    "chapel": 26,
    "bench": 12,
    "cave": 12,
    "kirche": 26,
    "prayer": 20,
    "cemetery": 18,
    "naica": 12,
}
SECTION_HINT_WEIGHTS = {
    "function": {"function": 10, "calling": 10, "api": 8, "workflow": 6, "tool": 6, "architecture": 5},
    "calling": {"function": 10, "calling": 10, "api": 8, "workflow": 6, "tool": 6, "architecture": 5},
    "agent": {"agent": 8, "agents": 8, "architecture": 6, "overview": 6, "workflow": 5},
    "openai": {"openai": 7, "agent": 4, "agents": 4},
}


def load_nanobanana_config(path: str | None) -> dict:
    defaults = {
        "mode": "generate",
        "base_url": "https://api.minimaxi.com/v1",
        "model": "image-01",
        "api_key_env": "MINIMAX_API_KEY",
        "image_size": "1K",
        "text_review_max_attempts": 3,
        "text_review_model": "MiniMax-M2.7",
        "text_review_base_url": "https://api.minimaxi.com/v1",
        "text_review_api_key_env": "MINIMAX_API_KEY",
        "text_review_api_format": "openai",
        "fetch_strategy": "official_then_wikimedia",
        "fallback_provider": "wikimedia",
        "request_timeout": 30,
        "official_page_limit": 8,
        "official_images_per_page": 6,
        "wikimedia_max_results": 8,
        "minimum_width": 640,
        "minimum_height": 360,
        "user_agent": DEFAULT_USER_AGENT,
        "infographic_reuse_floor": 20,
    }
    if not path:
        return defaults
    loaded = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    section = loaded.get("nanobanana", loaded)
    return {**defaults, **section}


def build_image_reviewer(config_path: str | None) -> OpenAICompatibleClient | None:
    try:
        llm_config = load_llm_config(config_path)
        image_config = load_nanobanana_config(config_path)
        review_config = {
            **llm_config,
            "model": image_config.get("text_review_model") or llm_config.get("model"),
            "base_url": image_config.get("text_review_base_url") or llm_config.get("base_url"),
            "api_key_env": image_config.get("text_review_api_key_env") or llm_config.get("api_key_env"),
            "api_format": image_config.get("text_review_api_format") or llm_config.get("api_format"),
            "temperature": 0.1,
        }
        if (
            review_config.get("api_format", "").lower() in {"openai", "anthropic"}
            and isinstance(review_config.get("base_url"), str)
            and (
                "api.minimaxi.com" in review_config["base_url"]
                or "api.minimax.io" in review_config["base_url"]
            )
        ):
            raise ValueError(
                "MiniMax OpenAI/Anthropic-compatible text APIs currently do not support image input, so text review is disabled for this profile."
            )
        return OpenAICompatibleClient(review_config)
    except ValueError as exc:
        print(f"[images] warning: text review disabled because reviewer config is unavailable: {exc}", file=sys.stderr)
        return None


def build_review_prompt(request: dict) -> str:
    descriptor = request.get("section_heading") or request.get("concept") or request.get("cover_copy") or request.get("title") or request.get("type", "image")
    return (
        f"Inspect this generated {request.get('type', 'image')} for a Chinese WeChat article about: {descriptor}.\n"
        "Required output standard: text-free imagery.\n"
        "Fail the image if you see any visible text, label, letter, number, watermark, pseudo-text, broken character, logo text, or UI copy anywhere in the image.\n"
        "Return JSON with these fields:\n"
        '{"status":"pass|fail","text_issue":true|false,"reason":"short explanation","problem_spans":["optional issue summaries"]}\n'
        "Pass only if the image is visually clean and text-free."
    )


def _fallback_parse_review_response(response: str) -> dict:
    lowered = response.lower()
    if '"status":"fail"' in lowered or '"status": "fail"' in lowered:
        status = "fail"
    elif '"status":"pass"' in lowered or '"status": "pass"' in lowered:
        status = "pass"
    elif "fail" in lowered and "pass" not in lowered:
        status = "fail"
    elif "pass" in lowered and "fail" not in lowered:
        status = "pass"
    else:
        raise ValueError(f"Could not infer review status from response: {response}")

    reason = ""
    marker = '"reason":"'
    marker_alt = '"reason": "'
    start = response.find(marker)
    marker_used = marker
    if start == -1:
        start = response.find(marker_alt)
        marker_used = marker_alt
    if start != -1:
        start += len(marker_used)
        end_candidates = [
            idx
            for idx in [
                response.find('\",\"problem_spans\"', start),
                response.find('\", \"problem_spans\"', start),
                response.find('\",}', start),
                response.find('"}', start),
            ]
            if idx != -1
        ]
        end = min(end_candidates) if end_candidates else -1
        if end != -1:
            reason = response[start:end]

    problem_spans = re.findall(r'"problem_spans"\s*:\s*\[(.*?)\]', response)
    spans: list[str] = []
    if problem_spans:
        spans = [item.strip().strip('"') for item in problem_spans[0].split(",") if item.strip()]

    return {
        "status": status,
        "text_issue": status == "fail",
        "reason": reason,
        "problem_spans": spans,
    }


def review_generated_image(reviewer: OpenAICompatibleClient, image_path: str, request: dict) -> dict:
    response = reviewer.chat_with_image(IMAGE_REVIEW_SYSTEM_PROMPT, build_review_prompt(request), image_path)
    try:
        payload = extract_json(response)
    except Exception:
        payload = _fallback_parse_review_response(response)
    status = str(payload.get("status", "")).strip().lower()
    text_issue = bool(payload.get("text_issue", False))
    reason = str(payload.get("reason", "")).strip()
    problem_spans = payload.get("problem_spans") or []
    if status not in {"pass", "fail"}:
        raise ValueError(f"Image review returned invalid status for {request.get('asset_id')}: {payload}")
    if status == "fail":
        text_issue = True
    return {
        "status": status,
        "text_issue": text_issue,
        "reason": reason,
        "problem_spans": [str(item).strip() for item in problem_spans if str(item).strip()],
    }


def build_generation_prompt(base_prompt: str, request: dict, review: dict | None, retry: bool) -> str:
    lines = [base_prompt.rstrip(), *TEXT_FREE_RULES]
    if request.get("visual_brief"):
        lines.append(f"Brief: {request['visual_brief']}. Semantic guidance only, not rendered text.")
    if request.get("type") == "infographic":
        lines.append("Infographic style: icons, arrows, nodes, blocks, and spacing only.")
    elif request.get("type") == "cover":
        lines.append("Cover style: bold editorial composition, abstract cues only.")
    else:
        lines.append("Inline style: symbolic illustration only, no annotations.")
    if retry:
        lines.append("Retry: regenerate from scratch and remove any text-like mark.")
    if review and review.get("reason"):
        reason = str(review["reason"]).strip()
        if reason:
            lines.append(f"Avoid previous issue: {reason[:180]}")

    prompt = "\n\n".join(line.strip() for line in lines if line and line.strip()).strip() + "\n"
    if len(prompt) > MAX_MINIMAX_PROMPT_LENGTH:
        compact_lines = [
            base_prompt.rstrip(),
            "Hard rule: no text, no Chinese, no English, no numbers, no labels, no pseudo-text, no garbled glyphs.",
            "Use icons, shapes, arrows, blocks, charts, and composition only.",
        ]
        if request.get("visual_brief"):
            compact_lines.append(f"Brief: {request['visual_brief']}")
        if request.get("type") == "infographic":
            compact_lines.append("Infographic only with icons and layout.")
        elif request.get("type") == "cover":
            compact_lines.append("Cover only with abstract editorial symbolism.")
        else:
            compact_lines.append("Inline only with symbolic illustration.")
        if retry:
            compact_lines.append("Retry: remove any text-like mark.")
        prompt = "\n\n".join(line.strip() for line in compact_lines if line and line.strip()).strip() + "\n"
    return prompt


def generate_asset_with_review(
    client: NanobananaClient,
    reviewer: OpenAICompatibleClient | None,
    request: dict,
    output_path: Path,
    max_attempts: int,
) -> dict:
    last_review: dict | None = None
    for attempt in range(1, max_attempts + 1):
        print(f"[images] generating {request.get('asset_id')} attempt {attempt}/{max_attempts}", file=sys.stderr)
        prompt = build_generation_prompt(request["prompt"], request, last_review, retry=attempt > 1)
        response = client.generate_image(prompt, request["aspect_ratio"])
        meta = client.save_first_image(response, str(output_path))
        meta["attempt"] = attempt
        meta["source_backend"] = "generated"
        if reviewer is None:
            meta["review"] = {"status": "skipped", "reason": "reviewer_unavailable"}
            return meta
        review = review_generated_image(reviewer, meta["path"], request)
        meta["review"] = review
        if review["status"] == "pass":
            return meta
        last_review = review
    raise ValueError(f"Image generation kept failing text review for {request.get('asset_id')}")


def _normalize_url(value: str) -> str:
    return value.strip()


def _is_youtube_url(url: str) -> bool:
    lowered = url.lower()
    return any(hint in lowered for hint in YOUTUBE_HINTS)


def _request_text(url: str, timeout: int, user_agent: str) -> str:
    request = Request(url, headers={"User-Agent": user_agent}, method="GET")
    try:
        with urlopen(request, timeout=timeout) as response:
            content_type = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(content_type, errors="replace")
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise HttpError(f"HTTP {exc.code} for {url}: {body[:300]}") from exc
    except URLError as exc:
        raise HttpError(f"Network error for {url}: {exc}") from exc


def _request_binary(url: str, timeout: int, user_agent: str) -> tuple[bytes, str]:
    request = Request(url, headers={"User-Agent": user_agent}, method="GET")
    try:
        with urlopen(request, timeout=timeout) as response:
            content_type = response.headers.get_content_type() or "application/octet-stream"
            return response.read(), content_type
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise HttpError(f"HTTP {exc.code} for {url}: {body[:300]}") from exc
    except URLError as exc:
        raise HttpError(f"Network error for {url}: {exc}") from exc


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        normalized = item.strip()
        if not normalized:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(normalized)
    return result


def _collect_official_page_urls(package: dict, limit: int) -> list[str]:
    urls: list[str] = []
    for note in package.get("source_notes", []):
        note_url = str(note.get("url") or "").strip()
        if note_url and not _is_youtube_url(note_url):
            urls.append(note_url)
        for source in note.get("sources", []):
            source_type = str(source.get("type") or "").strip().lower()
            source_url = str(source.get("url") or "").strip()
            if not source_url or _is_youtube_url(source_url):
                continue
            if source_type == "official_candidate":
                urls.append(source_url)
    deduped = _dedupe(urls)
    return deduped[: max(1, limit)]


def _extract_html_image_candidates(page_url: str, html_text: str, max_count: int) -> list[str]:
    candidates: list[str] = []
    for pattern in META_IMAGE_PATTERNS:
        for match in pattern.findall(html_text):
            candidates.append(urljoin(page_url, html.unescape(match)))
    for match in HTML_IMAGE_RE.findall(html_text):
        resolved = urljoin(page_url, html.unescape(match))
        lowered = resolved.lower()
        if any(hint in lowered for hint in BAD_IMAGE_HINTS):
            continue
        candidates.append(resolved)
        if len(candidates) >= max_count * 3:
            break
    return _dedupe(candidates)[: max(1, max_count)]


def _guess_extension(image_url: str, mime_type: str) -> str:
    parsed = urlparse(image_url)
    suffix = Path(parsed.path).suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".webp"}:
        return suffix
    if mime_type:
        guessed = mimetypes.guess_extension(mime_type)
        if guessed in {".jpg", ".jpeg", ".png", ".webp"}:
            return guessed
    return ".jpg"


def _download_image_candidate(image_url: str, output_base: Path, config: dict) -> dict:
    raw, mime_type = _request_binary(image_url, int(config.get("request_timeout", 30)), str(config.get("user_agent") or DEFAULT_USER_AGENT))
    with Image.open(io.BytesIO(raw)) as image:
        width, height = image.size
    if width < int(config.get("minimum_width", 640)) or height < int(config.get("minimum_height", 360)):
        raise ValueError(f"image too small: {width}x{height}")
    ext = _guess_extension(image_url, mime_type)
    output_path = output_base.with_suffix(ext)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(raw)
    return {
        "path": str(output_path),
        "mime_type": mime_type,
        "size_bytes": len(raw),
        "width": width,
        "height": height,
        "source_url": image_url,
    }


def _request_descriptor(request: dict, package: dict) -> str:
    for key in ("search_query", "section_heading", "concept", "cover_copy", "title"):
        value = str(request.get(key) or "").strip()
        if value:
            return value
    return str(package.get("final_title") or package.get("selected_title") or package.get("title") or "AI article").strip()


def _extract_wikimedia_value(payload: dict | None, key: str) -> str:
    if not payload:
        return ""
    value = payload.get(key) or {}
    if isinstance(value, dict):
        return str(value.get("value") or "").strip()
    return str(value or "").strip()


def _tokenize_relevance_text(text: str) -> list[str]:
    tokens: list[str] = []
    for raw in re.findall(r"[A-Za-z0-9][A-Za-z0-9+.-]*", text.lower()):
        if raw in RELEVANCE_STOP_WORDS:
            continue
        if len(raw) <= 2 and raw not in SHORT_KEEP_TOKENS:
            continue
        tokens.append(raw)
    return tokens


def _build_relevance_terms(request: dict, package: dict) -> set[str]:
    terms: set[str] = set()
    for key in ("search_query", "section_heading", "concept", "cover_copy", "title"):
        terms.update(_tokenize_relevance_text(str(request.get(key) or "")))
    terms.update(_tokenize_relevance_text(str(package.get("final_title") or package.get("selected_title") or package.get("title") or "")))
    task = package.get("task", {}) or {}
    terms.update(_tokenize_relevance_text(str(task.get("topic") or "")))
    for keyword in task.get("keywords", []) or []:
        terms.update(_tokenize_relevance_text(str(keyword or "")))
    for note in package.get("source_notes", []) or []:
        for source in note.get("sources", []) or []:
            entity = str(source.get("entity") or "").strip().lower()
            if entity:
                terms.add(entity)
    return {term for term in terms if term}


def _term_weight(term: str) -> int:
    if term in ENTITY_TERM_WEIGHTS:
        return ENTITY_TERM_WEIGHTS[term]
    if term == "ai":
        return 1
    if term in {"agent", "agents", "function", "calling", "workflow", "architecture", "overview", "diagram", "framework", "system", "api", "tool", "tools"}:
        return 3
    return 2 if len(term) >= 5 else 1


def _request_preferred_weights(request: dict) -> dict[str, int]:
    preferred = dict(TYPE_PREFERRED_WEIGHTS.get(str(request.get("type") or "").strip().lower(), {}))
    context_text = " ".join(str(request.get(key) or "") for key in ("section_heading", "search_query", "concept", "cover_copy", "title")).lower()
    for trigger, weights in SECTION_HINT_WEIGHTS.items():
        if trigger in context_text:
            for term, value in weights.items():
                preferred[term] = max(preferred.get(term, 0), value)
    return preferred


def _score_wikimedia_candidate(candidate: dict, request: dict, package: dict) -> int:
    title_text = str(candidate.get("title") or "")
    page_text = str(candidate.get("source_page_url") or "")
    haystack_title = title_text.lower()
    haystack_page = page_text.lower()
    combined = f"{haystack_title} {haystack_page}"
    score = 0

    for term in _build_relevance_terms(request, package):
        weight = _term_weight(term)
        if term in haystack_title:
            score += weight * 3
        elif term in haystack_page:
            score += weight

    for term, weight in _request_preferred_weights(request).items():
        if term in haystack_title:
            score += weight
        elif term in haystack_page:
            score += max(1, weight // 2)

    if "agent" in haystack_title and "ai" in haystack_title:
        score += 8
    if "function" in haystack_title and "call" in combined:
        score += 8
    if any(term in haystack_title for term in ("architecture", "workflow", "overview", "diagram")):
        score += 6

    for term, penalty in NEGATIVE_TERM_WEIGHTS.items():
        if term in combined:
            score -= penalty

    if str(request.get("type") or "").strip().lower() == "infographic" and any(term in combined for term in ("architecture", "workflow", "overview", "diagram", "framework")):
        score += 8

    return score


def _build_wikimedia_queries(request: dict, package: dict) -> list[str]:
    raw_queries: list[str] = []
    for key in ("search_query", "section_heading", "concept", "cover_copy", "title"):
        value = str(request.get(key) or "").strip()
        if value:
            raw_queries.append(value)

    article_title = str(package.get("final_title") or package.get("selected_title") or package.get("title") or "").strip()
    if article_title:
        raw_queries.append(article_title)

    task = package.get("task", {}) or {}
    for keyword in task.get("keywords", []) or []:
        value = str(keyword or "").strip()
        if value:
            raw_queries.append(value)

    for note in package.get("source_notes", []) or []:
        for source in note.get("sources", []) or []:
            entity = str(source.get("entity") or "").strip()
            if entity:
                raw_queries.append(entity)

    normalized_queries: list[str] = []
    seen: set[str] = set()
    for query in raw_queries:
        compact = " ".join(query.split())
        if not compact:
            continue
        lowered = compact.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        normalized_queries.append(compact)
        simplified = re.sub(r"[^A-Za-z0-9\s-]", " ", compact)
        simplified = " ".join(simplified.split())
        if simplified and simplified.lower() not in seen:
            seen.add(simplified.lower())
            normalized_queries.append(simplified)
    return normalized_queries[:8]


def _search_wikimedia_images(request: dict, package: dict, config: dict, http: JsonHttpClient) -> list[dict]:
    results: list[dict] = []
    seen_urls: set[str] = set()
    for query in _build_wikimedia_queries(request, package):
        params = {
            "action": "query",
            "format": "json",
            "generator": "search",
            "gsrsearch": f"filetype:bitmap {query}",
            "gsrnamespace": 6,
            "gsrlimit": int(config.get("wikimedia_max_results", 8)),
            "prop": "imageinfo|info",
            "inprop": "url",
            "iiprop": "url|mime|size|extmetadata",
            "iiurlwidth": 1600,
            "origin": "*",
        }
        url = "https://commons.wikimedia.org/w/api.php?" + urlencode(params)
        payload = http.get_json(url, headers={"User-Agent": str(config.get("user_agent") or DEFAULT_USER_AGENT)})
        pages = payload.get("query", {}).get("pages", {})
        for page in pages.values():
            info = (page.get("imageinfo") or [{}])[0]
            image_url = info.get("thumburl") or info.get("url")
            if not image_url:
                continue
            width = int(info.get("width") or 0)
            height = int(info.get("height") or 0)
            if width and height:
                min_width = int(config.get("minimum_width", 640))
                min_height = int(config.get("minimum_height", 360))
                if width < min_width or height < min_height:
                    continue
            lowered = str(image_url).lower()
            if lowered in seen_urls:
                continue
            seen_urls.add(lowered)
            extmetadata = info.get("extmetadata") or {}
            license_name = _extract_wikimedia_value(extmetadata, "LicenseShortName")
            artist = _extract_wikimedia_value(extmetadata, "Artist")
            credit = _extract_wikimedia_value(extmetadata, "Credit")
            source_page_url = page.get("canonicalurl") or page.get("fullurl") or ""
            candidate = {
                "image_url": image_url,
                "source_page_url": str(source_page_url),
                "title": str(page.get("title") or ""),
                "license": license_name,
                "credit": credit,
                "artist": artist,
                "width": width,
                "height": height,
                "source_backend": "wikimedia",
                "source_strategy": "fallback",
                "search_query": query,
            }
            candidate["relevance_score"] = _score_wikimedia_candidate(candidate, request, package)
            results.append(candidate)
    ranked = sorted(results, key=lambda item: (int(item.get("relevance_score", 0)), str(item.get("title") or "")), reverse=True)
    positive = [item for item in ranked if int(item.get("relevance_score", 0)) > 0]
    return positive or ranked


def _fetch_asset_from_sources(
    request: dict,
    package: dict,
    output_base: Path,
    config: dict,
    http: JsonHttpClient,
    page_cache: dict[str, list[str]],
    used_image_urls: set[str],
    allow_reuse: bool = False,
    reuse_score_floor: int = 0,
) -> dict:
    page_urls = _collect_official_page_urls(package, int(config.get("official_page_limit", 8)))
    for page_url in page_urls:
        if page_url not in page_cache:
            try:
                html_text = _request_text(page_url, int(config.get("request_timeout", 30)), str(config.get("user_agent") or DEFAULT_USER_AGENT))
            except Exception as exc:
                print(f"[images] skipped official page for {request.get('asset_id')}: {page_url} ({exc})", file=sys.stderr)
                page_cache[page_url] = []
            else:
                page_cache[page_url] = _extract_html_image_candidates(page_url, html_text, int(config.get("official_images_per_page", 6)))
        for image_url in page_cache.get(page_url, []):
            lowered = image_url.lower()
            if lowered in used_image_urls:
                continue
            try:
                meta = _download_image_candidate(image_url, output_base, config)
            except Exception as exc:
                print(f"[images] skipped official candidate for {request.get('asset_id')}: {image_url} ({exc})", file=sys.stderr)
                continue
            used_image_urls.add(lowered)
            return {
                **meta,
                "source_backend": "official_fetch",
                "source_strategy": "official",
                "source_page_url": page_url,
                "review": {"status": "skipped", "reason": "official_fetch_no_editing"},
            }

    if str(config.get("fallback_provider") or "").lower() != "wikimedia":
        raise ValueError(f"No official image found for {request.get('asset_id')} and fallback provider is disabled")

    unused_candidates: list[dict] = []
    reused_candidates: list[dict] = []
    for candidate in _search_wikimedia_images(request, package, config, http):
        image_url = str(candidate.get("image_url") or "").strip()
        if not image_url:
            continue
        lowered = image_url.lower()
        if lowered in used_image_urls:
            if allow_reuse:
                reused_candidates.append(candidate)
            continue
        unused_candidates.append(candidate)

    preferred_candidates: list[tuple[dict, bool]] = []
    if allow_reuse and reused_candidates:
        top_unused_score = int(unused_candidates[0].get("relevance_score", 0)) if unused_candidates else -1
        top_reuse_score = int(reused_candidates[0].get("relevance_score", 0))
        if top_unused_score < reuse_score_floor and top_reuse_score >= reuse_score_floor:
            preferred_candidates.extend((candidate, True) for candidate in reused_candidates)
            preferred_candidates.extend((candidate, False) for candidate in unused_candidates)
        else:
            preferred_candidates.extend((candidate, False) for candidate in unused_candidates)
            preferred_candidates.extend((candidate, True) for candidate in reused_candidates)
    else:
        preferred_candidates.extend((candidate, False) for candidate in unused_candidates)

    seen_attempt_urls: set[str] = set()
    for candidate, reused_candidate in preferred_candidates:
        image_url = str(candidate.get("image_url") or "").strip()
        lowered = image_url.lower()
        if not image_url or lowered in seen_attempt_urls:
            continue
        seen_attempt_urls.add(lowered)
        try:
            meta = _download_image_candidate(image_url, output_base, config)
        except Exception as exc:
            print(f"[images] skipped wikimedia candidate for {request.get('asset_id')}: {image_url} ({exc})", file=sys.stderr)
            continue
        used_image_urls.add(lowered)
        source_strategy = str(candidate.get("source_strategy", "fallback"))
        if reused_candidate:
            source_strategy = f"{source_strategy}_reuse"
        return {
            **meta,
            "source_backend": candidate.get("source_backend", "wikimedia"),
            "source_strategy": source_strategy,
            "source_page_url": candidate.get("source_page_url", ""),
            "license": candidate.get("license", ""),
            "credit": candidate.get("credit", ""),
            "artist": candidate.get("artist", ""),
            "relevance_score": int(candidate.get("relevance_score", 0)),
            "review": {"status": "skipped", "reason": "fetched_source_no_editing"},
        }

    raise ValueError(f"Unable to find a usable fetched image for {request.get('asset_id')}")


def execute_fetch_mode(package: dict, image_package: dict, config: dict, asset_dir: Path) -> dict:
    http = JsonHttpClient(timeout=int(config.get("request_timeout", 30)))
    page_cache: dict[str, list[str]] = {}
    used_image_urls: set[str] = set()
    generated_assets: list[dict] = []

    requests: list[dict] = [image_package["cover_request"], *image_package.get("inline_requests", [])]
    info_request = image_package.get("infographic_request")
    if info_request:
        requests.append(info_request)

    cover_path = ""
    for request in requests:
        output_base = asset_dir / request["asset_id"]
        allow_reuse = request.get("type") == "infographic"
        reuse_score_floor = int(config.get("infographic_reuse_floor", 20)) if allow_reuse else 0
        meta = _fetch_asset_from_sources(
            request,
            package,
            output_base,
            config,
            http,
            page_cache,
            used_image_urls,
            allow_reuse=allow_reuse,
            reuse_score_floor=reuse_score_floor,
        )
        combined = {**request, **meta}
        generated_assets.append(combined)
        if request.get("asset_id") == "cover-001":
            cover_path = meta["path"]

    image_package["execution_status"] = "completed"
    image_package["generated_assets"] = generated_assets
    image_package["cover_image_path"] = cover_path
    image_package["text_review_enabled"] = False
    image_package["text_review_max_attempts"] = 0
    image_package["image_mode"] = "fetch"
    image_package["fetch_strategy"] = config.get("fetch_strategy", "official_then_wikimedia")
    return image_package


def execute_generate_mode(package: dict, image_package: dict, config: dict, asset_dir: Path, config_path: str | None) -> dict:
    api_key = os.getenv(config["api_key_env"])
    if not api_key:
        raise ValueError(f"Missing env var: {config['api_key_env']}")

    client = NanobananaClient(api_key=api_key, base_url=config["base_url"], model=config["model"], image_size=config["image_size"])
    reviewer = build_image_reviewer(config_path)
    generated_assets: list[dict] = []
    max_attempts = max(1, int(config.get("text_review_max_attempts", 3)))

    cover_meta = generate_asset_with_review(client, reviewer, image_package["cover_request"], asset_dir / "cover-001.png", max_attempts)
    generated_assets.append({**image_package["cover_request"], **cover_meta})

    for request in image_package.get("inline_requests", []):
        meta = generate_asset_with_review(client, reviewer, request, asset_dir / f"{request['asset_id']}.png", max_attempts)
        generated_assets.append({**request, **meta})

    info_request = image_package.get("infographic_request")
    if info_request:
        meta = generate_asset_with_review(client, reviewer, info_request, asset_dir / f"{info_request['asset_id']}.png", max_attempts)
        generated_assets.append({**info_request, **meta})

    image_package["execution_status"] = "completed"
    image_package["generated_assets"] = generated_assets
    image_package["cover_image_path"] = cover_meta["path"]
    image_package["text_review_enabled"] = reviewer is not None
    image_package["text_review_max_attempts"] = max_attempts
    image_package["image_mode"] = "generate"
    return image_package


def main() -> None:
    parser = argparse.ArgumentParser(description="Build or execute image request manifests.")
    parser.add_argument("input", help="Path to final or formatted article JSON.")
    parser.add_argument("--output", required=True, help="Path to image request JSON.")
    parser.add_argument("--execute", action="store_true", help="Execute the configured image backend.")
    parser.add_argument("--config", help="Optional config JSON path. Accepts either a dedicated image config or a merged live config with a nanobanana section.")
    parser.add_argument("--asset-dir", help="Directory where generated or fetched images should be stored.")
    args = parser.parse_args()

    package = json.loads(Path(args.input).read_text(encoding="utf-8-sig"))
    image_package = build_image_requests(package)

    if args.execute:
        config = load_nanobanana_config(args.config)
        asset_dir = Path(args.asset_dir or (Path(args.output).parent / "generated-images"))
        asset_dir.mkdir(parents=True, exist_ok=True)
        mode = str(config.get("mode") or "generate").strip().lower()
        if mode == "fetch":
            image_package = execute_fetch_mode(package, image_package, config, asset_dir)
        else:
            image_package = execute_generate_mode(package, image_package, config, asset_dir, args.config)
    else:
        image_package["execution_status"] = "planned"
        image_package["image_mode"] = "planned"

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(image_package, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
