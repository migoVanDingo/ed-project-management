from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, AsyncIterator


@dataclass
class LLMStreamEvent:
    delta: str = ""
    usage: dict[str, Any] | None = None


class LLMProvider(ABC):
    name: str

    @abstractmethod
    async def stream_chat(
        self,
        *,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
    ) -> AsyncIterator[LLMStreamEvent]:
        raise NotImplementedError
