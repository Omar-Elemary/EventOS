import json
from typing import Any

import httpx
from pydantic import BaseModel, ValidationError

from app.core.http import get_http_client
from app.llm.base import LLMError, LLMMessage, LLMProvider


class OpenAICompatibleProvider(LLMProvider):
    name = "openai_compatible"

    def __init__(self, api_key: str, model: str, base_url: str, timeout: float = 25.0) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.name = "groq" if "groq.com" in self.base_url else "openai_compatible"

    async def complete_structured(
        self,
        schema: type[BaseModel],
        messages: list[LLMMessage],
        *,
        tools: list[dict[str, Any]] | None = None,
    ) -> BaseModel:
        if not self.api_key:
            raise LLMError("LLM_API_KEY is empty for openai_compatible provider")
        groq = "groq.com" in self.base_url
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": 0.1,
            "max_tokens": 800,
        }
        if groq:
            payload["response_format"] = {"type": "json_object"}
            payload["messages"] = [
                {
                    "role": "system",
                    "content": "Return a JSON object only. Use this schema: " + json.dumps(schema.model_json_schema()),
                },
                *payload["messages"],
            ]
        else:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": schema.__name__[:64],
                    "strict": False,
                    "schema": schema.model_json_schema(),
                },
            }
        last_error: Exception | None = None
        client = get_http_client(timeout=self.timeout)
        for attempt in range(2):
            try:
                res = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json=payload,
                    timeout=self.timeout,
                )
                if res.status_code == 400 and payload.get("response_format", {}).get("type") == "json_schema":
                    payload["response_format"] = {"type": "json_object"}
                    last_error = httpx.HTTPStatusError("json_schema unsupported", request=res.request, response=res)
                    continue
                res.raise_for_status()
                data = res.json()
                content = data["choices"][0]["message"]["content"]
                if isinstance(content, list):
                    content = "".join(part.get("text", "") if isinstance(part, dict) else str(part) for part in content)
                if isinstance(content, str):
                    text = content.strip()
                    if text.startswith("```"):
                        text = text.split("\n", 1)[-1]
                        if text.endswith("```"):
                            text = text[: -3].strip()
                    content = text
                return schema.model_validate_json(content)
            except (httpx.HTTPError, ValidationError, KeyError, TypeError, json.JSONDecodeError) as exc:
                last_error = exc
                payload["messages"] = payload["messages"] + [
                    {
                        "role": "user",
                        "content": "Return valid JSON matching the schema only. No markdown.",
                    }
                ]
        raise LLMError(str(last_error)) from last_error
