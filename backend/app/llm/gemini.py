import json
from typing import Any

import httpx
from pydantic import BaseModel, ValidationError

from app.core.http import get_http_client
from app.llm.base import LLMError, LLMMessage, LLMProvider


class GeminiProvider(LLMProvider):
    name = "gemini"

    def __init__(self, api_key: str, model: str, base_url: str, timeout: float = 25.0) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def complete_structured(
        self,
        schema: type[BaseModel],
        messages: list[LLMMessage],
        *,
        tools: list[dict[str, Any]] | None = None,
    ) -> BaseModel:
        if not self.api_key:
            raise LLMError("LLM_API_KEY is empty for gemini provider")
        contents = []
        for m in messages:
            if m.role == "system":
                contents.append({"role": "user", "parts": [{"text": f"System: {m.content}"}]})
            elif m.role == "assistant":
                contents.append({"role": "model", "parts": [{"text": m.content}]})
            else:
                contents.append({"role": "user", "parts": [{"text": m.content}]})
        url = f"{self.base_url}/models/{self.model}:generateContent"
        payload: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json",
            },
        }
        last_error: Exception | None = None
        client = get_http_client(timeout=self.timeout)
        for _ in range(2):
            try:
                res = await client.post(url, params={"key": self.api_key}, json=payload, timeout=self.timeout)
                res.raise_for_status()
                data = res.json()
                parts = data["candidates"][0]["content"]["parts"]
                text = "".join(str(p.get("text") or "") for p in parts)
                return schema.model_validate_json(text)
            except (httpx.HTTPError, ValidationError, KeyError, TypeError, json.JSONDecodeError) as exc:
                last_error = exc
                payload["contents"] = payload["contents"] + [
                    {"role": "user", "parts": [{"text": "Return valid JSON matching the schema only. No markdown."}]}
                ]
        raise LLMError(str(last_error)) from last_error
