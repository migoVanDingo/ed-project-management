from __future__ import annotations

from platform_common.config.settings import get_settings

from services.llm.anthropic_provider import AnthropicProvider
from services.llm.openai_provider import OpenAIProvider
from services.llm.provider_interface import LLMProvider


class ProviderFactory:
    def __init__(self) -> None:
        self._providers: dict[str, type[LLMProvider]] = {
            OpenAIProvider.name: OpenAIProvider,
            AnthropicProvider.name: AnthropicProvider,
        }

    def create(self, provider_name: str | None = None) -> LLMProvider:
        resolved_name = (provider_name or get_settings().llm_default_provider).strip().lower()
        provider_cls = self._providers.get(resolved_name)
        if provider_cls is None:
            raise RuntimeError(f"Unsupported LLM provider '{resolved_name}'")
        return provider_cls()
