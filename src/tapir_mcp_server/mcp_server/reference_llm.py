"""Client for optional reference LLM calls via Ollama."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class OllamaConfig:
    """Settings for the local Ollama endpoint."""

    base_url: str
    model: str


def ask_reference_llm(
    config: OllamaConfig,
    prompt: str,
    system_prompt: str | None = None,
    temperature: float = 0.2,
) -> dict[str, Any]:
    """Ask the configured Ollama model for reference guidance."""
    payload = {
        "model": config.model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": temperature},
    }
    if system_prompt:
        payload["system"] = system_prompt

    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url=f"{config.base_url.rstrip('/')}/api/generate",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as err:
        detail = err.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Ollama HTTP error {err.code}: {detail}") from err
    except urllib.error.URLError as err:
        raise RuntimeError(
            "Could not reach Ollama. Set OLLAMA_BASE_URL to your endpoint."
        ) from err

    data = json.loads(raw)
    return {
        "model": data.get("model", config.model),
        "response": data.get("response", ""),
        "done": bool(data.get("done", False)),
        "done_reason": data.get("done_reason"),
        "total_duration": data.get("total_duration"),
    }
