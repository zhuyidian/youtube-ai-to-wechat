from __future__ import annotations

import base64
import json
import mimetypes
import os
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


@dataclass
class NanobananaRequest:
    prompt: str
    aspect_ratio: str


@dataclass
class WeChatDraftRequest:
    title: str
    digest: str
    content_html: str
    cover_path: str


class HttpError(RuntimeError):
    pass


class JsonHttpClient:
    def __init__(self, timeout: int = 60) -> None:
        self.timeout = timeout

    def get_json(self, url: str, headers: Optional[dict[str, str]] = None) -> dict[str, Any]:
        request = Request(url, headers=headers or {}, method="GET")
        try:
            with urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise HttpError(f"HTTP {exc.code} for {url}: {body}") from exc

    def post_json(self, url: str, payload: dict[str, Any], headers: Optional[dict[str, str]] = None) -> dict[str, Any]:
        merged_headers = {"Content-Type": "application/json", **(headers or {})}
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = Request(url, data=body, headers=merged_headers, method="POST")
        try:
            with urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            response_body = exc.read().decode("utf-8", errors="replace")
            raise HttpError(f"HTTP {exc.code} for {url}: {response_body}") from exc

    def post_multipart(self, url: str, file_field: str, file_path: str, fields: Optional[dict[str, str]] = None, headers: Optional[dict[str, str]] = None) -> dict[str, Any]:
        boundary = uuid.uuid4().hex
        parts: list[bytes] = []
        for name, value in (fields or {}).items():
            parts.extend([
                f"--{boundary}\r\n".encode("utf-8"),
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"),
                str(value).encode("utf-8"),
                b"\r\n",
            ])
        file_bytes = Path(file_path).read_bytes()
        mime_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
        filename = Path(file_path).name
        parts.extend([
            f"--{boundary}\r\n".encode("utf-8"),
            (f'Content-Disposition: form-data; name="{file_field}"; filename="{filename}"\r\n' f"Content-Type: {mime_type}\r\n\r\n").encode("utf-8"),
            file_bytes,
            b"\r\n",
            f"--{boundary}--\r\n".encode("utf-8"),
        ])
        body = b"".join(parts)
        merged_headers = {"Content-Type": f"multipart/form-data; boundary={boundary}", **(headers or {})}
        request = Request(url, data=body, headers=merged_headers, method="POST")
        try:
            with urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            response_body = exc.read().decode("utf-8", errors="replace")
            raise HttpError(f"HTTP {exc.code} for {url}: {response_body}") from exc


class YouTubeDataApiClient:
    BASE_URL = "https://www.googleapis.com/youtube/v3"

    def __init__(self, api_key: Optional[str] = None, fixtures_dir: Optional[str] = None, timeout: int = 20) -> None:
        self.api_key = api_key or os.getenv("YOUTUBE_API_KEY")
        self.fixtures_dir = Path(fixtures_dir) if fixtures_dir else None
        self.timeout = timeout
        if not self.fixtures_dir and not self.api_key:
            raise ValueError("Set YOUTUBE_API_KEY or pass --fixtures-dir for offline testing.")

    def search_videos(self, query: str, published_after: Optional[str] = None, max_results: int = 10, relevance_language: Optional[str] = None, region_code: Optional[str] = None) -> dict[str, Any]:
        params: dict[str, Any] = {"part": "snippet", "type": "video", "q": query, "maxResults": max_results, "order": "date"}
        if published_after:
            params["publishedAfter"] = published_after
        if relevance_language:
            params["relevanceLanguage"] = relevance_language
        if region_code:
            params["regionCode"] = region_code
        return self._request("search", params)

    def get_videos(self, video_ids: list[str]) -> dict[str, Any]:
        if not video_ids:
            return {"items": []}
        return self._request("videos", {"part": "snippet,contentDetails,statistics", "id": ",".join(video_ids), "maxResults": len(video_ids)})

    def get_channels(self, channel_ids: list[str]) -> dict[str, Any]:
        if not channel_ids:
            return {"items": []}
        return self._request("channels", {"part": "snippet,statistics", "id": ",".join(channel_ids), "maxResults": len(channel_ids)})

    def _request(self, resource: str, params: dict[str, Any]) -> dict[str, Any]:
        if self.fixtures_dir:
            fixture_path = self.fixtures_dir / f"{resource}.json"
            return json.loads(fixture_path.read_text(encoding="utf-8-sig"))
        assert self.api_key is not None
        query = urlencode({**params, "key": self.api_key})
        url = f"{self.BASE_URL}/{resource}?{query}"
        with urlopen(url, timeout=self.timeout) as response:
            return json.loads(response.read().decode("utf-8"))


def resolve_image_backend(api_key: str, base_url: str) -> tuple[str, str]:
    normalized = base_url.rstrip("/")
    if "api.apicore.ai" in normalized:
        return "apicore", normalized
    if "api.minimaxi.com" in normalized or "api.minimax.io" in normalized:
        return "minimax", normalized
    if api_key.startswith("AIza") and "nanobananai.com" in normalized:
        return "gemini", "https://generativelanguage.googleapis.com"
    return "gemini", normalized


def normalize_gemini_aspect_ratio(base_url: str, aspect_ratio: str) -> str:
    normalized = aspect_ratio.strip()
    if "api.minimaxi.com" in base_url or "api.minimax.io" in base_url:
        aspect_map = {
            "2.35:1": "21:9",
            "4:5": "3:4",
        }
        return aspect_map.get(normalized, normalized)
    if "generativelanguage.googleapis.com" in base_url and normalized == "2.35:1":
        return "21:9"
    return normalized


class NanobananaClient:
    def __init__(self, api_key: str, base_url: str = "https://api.nanobananai.com", model: str = "gemini-3-pro-image-preview", timeout: int = 120, image_size: str = "1K") -> None:
        self.api_key = api_key
        self.backend, self.base_url = resolve_image_backend(api_key, base_url)
        self.model = model
        self.timeout = timeout
        self.image_size = image_size
        self.http = JsonHttpClient(timeout=timeout)

    def generate_image(self, prompt: str, aspect_ratio: str) -> dict[str, Any]:
        if self.backend == "apicore":
            return self._generate_image_apicore(prompt, aspect_ratio)
        if self.backend == "minimax":
            return self._generate_image_minimax(prompt, aspect_ratio)
        return self._generate_image_gemini(prompt, aspect_ratio)

    def _generate_image_gemini(self, prompt: str, aspect_ratio: str) -> dict[str, Any]:
        url = f"{self.base_url}/v1beta/models/{self.model}:generateContent"
        resolved_aspect_ratio = normalize_gemini_aspect_ratio(self.base_url, aspect_ratio)
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": resolved_aspect_ratio, "imageSize": self.image_size}},
        }
        return self.http.post_json(url, payload, headers={"x-goog-api-key": self.api_key})

    def _generate_image_apicore(self, prompt: str, aspect_ratio: str) -> dict[str, Any]:
        url = f"{self.base_url}/v1/chat/completions"
        payload = {
            "model": self.model,
            "stream": False,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        }
        return self.http.post_json(url, payload, headers={"Authorization": f"Bearer {self.api_key}", "User-Agent": "curl/8.0"})

    def _generate_image_minimax(self, prompt: str, aspect_ratio: str) -> dict[str, Any]:
        endpoint = f"{self.base_url}/image_generation" if self.base_url.endswith("/v1") else f"{self.base_url}/v1/image_generation"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "aspect_ratio": normalize_gemini_aspect_ratio(self.base_url, aspect_ratio),
            "response_format": "base64",
            "n": 1,
        }
        return self.http.post_json(endpoint, payload, headers={"Authorization": f"Bearer {self.api_key}"})

    def save_first_image(self, response: dict[str, Any], output_path: str) -> dict[str, Any]:
        for image_payload in self._iter_image_payloads(response):
            if image_payload["kind"] == "base64":
                raw = base64.b64decode(image_payload["data"])
                path = Path(output_path)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)
                return {"path": str(path), "mime_type": image_payload.get("mime_type") or "image/png", "size_bytes": len(raw)}
            if image_payload["kind"] == "url":
                raw, mime_type = self._download_image(image_payload["url"])
                path = Path(output_path)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)
                return {"path": str(path), "mime_type": mime_type, "size_bytes": len(raw), "source_url": image_payload["url"]}
        raise HttpError(f"Image response did not include usable image data. Top-level keys: {sorted(response.keys())}")

    def _iter_image_payloads(self, response: dict[str, Any]):
        for candidate in response.get("candidates", []):
            for part in candidate.get("content", {}).get("parts", []):
                inline_data = part.get("inlineData") or part.get("inline_data")
                if inline_data and inline_data.get("data"):
                    yield {"kind": "base64", "data": inline_data["data"], "mime_type": inline_data.get("mimeType") or inline_data.get("mime_type") or "image/png"}

        data_field = response.get("data", [])
        if isinstance(data_field, dict):
            for b64_image in data_field.get("image_base64", []):
                if b64_image:
                    yield {"kind": "base64", "data": b64_image, "mime_type": "image/jpeg"}
            for image_url in data_field.get("image_urls", []):
                if image_url:
                    yield {"kind": "url", "url": image_url}

        for item in data_field if isinstance(data_field, list) else []:
            if isinstance(item, dict):
                if item.get("b64_json"):
                    yield {"kind": "base64", "data": item["b64_json"], "mime_type": "image/png"}
                if item.get("url"):
                    yield {"kind": "url", "url": item["url"]}

        for choice in response.get("choices", []):
            message = choice.get("message", {}) if isinstance(choice, dict) else {}
            for image in message.get("images", []):
                if not isinstance(image, dict):
                    continue
                image_url = image.get("image_url") or {}
                url = image_url.get("url") or image.get("url")
                if url:
                    yield from self._coerce_url_payload(url)
                b64_json = image.get("b64_json") or image_url.get("b64_json")
                if b64_json:
                    yield {"kind": "base64", "data": b64_json, "mime_type": "image/png"}

            content = message.get("content")
            if isinstance(content, list):
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    if block.get("type") == "image_url":
                        image_url = block.get("image_url") or {}
                        url = image_url.get("url") or block.get("url")
                        if url:
                            yield from self._coerce_url_payload(url)
                    if block.get("type") == "output_text" and block.get("text"):
                        yield from self._extract_urls_from_text(block["text"])
            elif isinstance(content, str):
                yield from self._extract_urls_from_text(content)

    def _coerce_url_payload(self, url: str):
        if url.startswith("data:image/"):
            header, encoded = url.split(",", 1)
            mime_type = header.split(";")[0].split(":", 1)[1]
            yield {"kind": "base64", "data": encoded, "mime_type": mime_type}
            return
        yield {"kind": "url", "url": url}

    def _extract_urls_from_text(self, text: str):
        for match in re.findall(r"data:image/[^\s'\"]+", text):
            yield from self._coerce_url_payload(match)
        for match in re.findall(r"https?://[^\s'\")]+", text):
            yield {"kind": "url", "url": match}

    def _download_image(self, url: str) -> tuple[bytes, str]:
        request = Request(url, method="GET")
        with urlopen(request, timeout=self.timeout) as response:
            raw = response.read()
            mime_type = response.headers.get("Content-Type", "image/png").split(";", 1)[0]
        return raw, mime_type


class WeChatOfficialAccountClient:
    def __init__(self, base_url: str = "https://api.weixin.qq.com", access_token: Optional[str] = None, app_id: Optional[str] = None, app_secret: Optional[str] = None, timeout: int = 60) -> None:
        self.base_url = base_url.rstrip("/")
        self.access_token = access_token
        self.app_id = app_id
        self.app_secret = app_secret
        self.http = JsonHttpClient(timeout=timeout)

    def resolve_access_token(self) -> str:
        if self.access_token:
            return self.access_token
        if not self.app_id or not self.app_secret:
            raise ValueError("Set WECHAT_ACCESS_TOKEN or both WECHAT_APP_ID and WECHAT_APP_SECRET.")
        params = urlencode({"grant_type": "client_credential", "appid": self.app_id, "secret": self.app_secret})
        response = self.http.get_json(f"{self.base_url}/cgi-bin/token?{params}")
        token = response.get("access_token")
        if not token:
            raise HttpError(f"Failed to fetch WeChat access token: {response}")
        self.access_token = token
        return token

    def upload_material(self, file_path: str, media_type: str = "thumb") -> dict[str, Any]:
        token = self.resolve_access_token()
        response = self.http.post_multipart(f"{self.base_url}/cgi-bin/material/add_material?access_token={token}&type={media_type}", file_field="media", file_path=file_path)
        if response.get("errcode") not in (None, 0):
            raise HttpError(f"WeChat material upload failed: {response}")
        return response

    def upload_article_image(self, file_path: str) -> dict[str, Any]:
        token = self.resolve_access_token()
        response = self.http.post_multipart(f"{self.base_url}/cgi-bin/media/uploadimg?access_token={token}", file_field="media", file_path=file_path)
        if response.get("errcode") not in (None, 0):
            raise HttpError(f"WeChat article image upload failed: {response}")
        return response

    def add_draft(self, payload: dict[str, Any]) -> dict[str, Any]:
        token = self.resolve_access_token()
        response = self.http.post_json(f"{self.base_url}/cgi-bin/draft/add?access_token={token}", payload)
        if response.get("errcode") not in (None, 0):
            raise HttpError(f"WeChat draft add failed: {response}")
        return response



