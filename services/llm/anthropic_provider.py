from __future__ import annotations

from typing import AsyncIterator

from services.llm.provider_interface import LLMProvider, LLMStreamEvent


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    async def stream_chat(
        self,
        *,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
    ) -> AsyncIterator[LLMStreamEvent]:
        raise RuntimeError(
            "Anthropic streaming is not implemented in this service yet"
        )
        yield LLMStreamEvent()
