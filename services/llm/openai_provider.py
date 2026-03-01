from __future__ import annotations

from typing import AsyncIterator

from platform_common.config.settings import get_settings

from services.llm.provider_interface import LLMProvider, LLMStreamEvent

try:
    from openai import AsyncOpenAI
except ImportError:  # pragma: no cover - dependency resolved in service image
    AsyncOpenAI = None  # type: ignore[assignment]


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self) -> None:
        settings = get_settings()
        if AsyncOpenAI is None:
            raise RuntimeError("openai package is not installed")
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def stream_chat(
        self,
        *,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
    ) -> AsyncIterator[LLMStreamEvent]:
        stream = await self._client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            stream=True,
            stream_options={"include_usage": True},
        )

        async for chunk in stream:
            if chunk.choices:
                delta = chunk.choices[0].delta.content or ""
                if delta:
                    yield LLMStreamEvent(delta=delta)

            usage = getattr(chunk, "usage", None)
            if usage:
                usage_json = usage.model_dump() if hasattr(usage, "model_dump") else dict(usage)
                yield LLMStreamEvent(usage=usage_json)
