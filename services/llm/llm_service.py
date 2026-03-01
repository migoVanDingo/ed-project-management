from __future__ import annotations

from dataclasses import dataclass
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from platform_common.config.settings import get_settings

from services.llm.context_builder import ContextBuildResult, build_context
from services.llm.provider_factory import ProviderFactory
from services.llm.provider_interface import LLMStreamEvent


@dataclass
class LLMRequest:
    provider: str
    model: str
    temperature: float
    context: ContextBuildResult


class LLMService:
    def __init__(self, provider_factory: ProviderFactory | None = None) -> None:
        self._settings = get_settings()
        self._provider_factory = provider_factory or ProviderFactory()

    async def build_request(
        self,
        *,
        session: AsyncSession,
        conversation_id: str,
    ) -> LLMRequest:
        context = await build_context(session, conversation_id)
        return LLMRequest(
            provider=self._settings.llm_default_provider,
            model=context.project.llm_model_override or self._settings.llm_default_model,
            temperature=self._settings.llm_temperature,
            context=context,
        )

    async def stream_chat(self, request: LLMRequest) -> AsyncIterator[LLMStreamEvent]:
        provider = self._provider_factory.create(request.provider)
        async for event in provider.stream_chat(
            messages=request.context.messages,
            model=request.model,
            temperature=request.temperature,
        ):
            yield event
