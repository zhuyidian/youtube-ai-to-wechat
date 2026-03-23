from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen


def load_llm_config(path: str | None) -> dict:
    defaults = {
        "api_format": "openai",
        "base_url": "https://api.openai.com/v1",
        "api_key_env": "OPENAI_API_KEY",
        "model": "gpt-4.1-mini",
        "temperature": 0.7,
        "timeout": 120,
        "json_mode": False,
        "max_tokens": 4000,
        "anthropic_version": "2023-06-01",
        "headers": {},
    }
    if not path:
        return defaults
    loaded = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    section = loaded.get("llm", loaded)
    return {**defaults, **section}


class OpenAICompatibleClient:
    def __init__(self, config: dict) -> None:
        self.config = config
        self.api_format = config.get("api_format", "openai").lower()
        self.base_url = config["base_url"].rstrip("/")
        self.api_key = os.getenv(config["api_key_env"])
        if not self.api_key:
            raise ValueError(f"Missing env var: {config['api_key_env']}")

    def chat(self, system_prompt: str, user_prompt: str) -> str:
        if self.api_format == "anthropic":
            return self._chat_anthropic(system_prompt, user_prompt)
        return self._chat_openai(system_prompt, user_prompt)

    def _chat_openai(self, system_prompt: str, user_prompt: str) -> str:
        payload: dict[str, Any] = {
            "model": self.config["model"],
            "temperature": self.config.get("temperature", 0.7),
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        if self.config.get("json_mode"):
            payload["response_format"] = {"type": "json_object"}

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            **self.config.get("headers", {}),
        }
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = Request(f"{self.base_url}/chat/completions", data=body, headers=headers, method="POST")
        with urlopen(request, timeout=self.config.get("timeout", 120)) as response:
            data = json.loads(response.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"]

    def _chat_anthropic(self, system_prompt: str, user_prompt: str) -> str:
        payload: dict[str, Any] = {
            "model": self.config["model"],
            "max_tokens": self.config.get("max_tokens", 4000),
            "temperature": self.config.get("temperature", 0.7),
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": user_prompt},
            ],
        }

        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": self.config.get("anthropic_version", "2023-06-01"),
            **self.config.get("headers", {}),
        }
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = Request(f"{self.base_url}/v1/messages", data=body, headers=headers, method="POST")
        with urlopen(request, timeout=self.config.get("timeout", 120)) as response:
            data = json.loads(response.read().decode("utf-8"))

        content = data.get("content", [])
        if isinstance(content, str):
            return content
        text_parts: list[str] = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text_parts.append(block.get("text", ""))
        if not text_parts:
            raise ValueError("Anthropic-compatible response did not contain text content")
        return "\n\n".join(part for part in text_parts if part)


def _extract_first_json_object(text: str) -> str:
    start = text.find("{")
    if start == -1:
        raise json.JSONDecodeError("No JSON object found", text, 0)

    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        ch = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue

        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]

    raise json.JSONDecodeError("Unterminated JSON object", text, start)


def extract_json(text: str) -> dict:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        if stripped.startswith("json"):
            stripped = stripped[4:].strip()
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        return json.loads(_extract_first_json_object(stripped))
