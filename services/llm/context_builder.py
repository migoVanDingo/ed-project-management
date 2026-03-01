from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from platform_common.config.settings import get_settings
from platform_common.db.dal.project_conversation_dal import ProjectConversationDAL
from platform_common.db.dal.project_conversation_message_dal import (
    ProjectConversationMessageDAL,
)
from platform_common.db.dal.project_dal import ProjectDAL
from platform_common.errors.base import NotFoundError
from platform_common.models.project import Project
from platform_common.models.project_conversation import ProjectConversation

DEFAULT_PROJECT_SYSTEM_PROMPT = (
    "You are Lucy, an intelligent AI assistant helping with this project."
)


@dataclass
class ContextBuildResult:
    conversation: ProjectConversation
    project: Project
    messages: list[dict[str, str]]


async def build_context(
    session: AsyncSession,
    conversation_id: str,
) -> ContextBuildResult:
    settings = get_settings()
    conversation = await ProjectConversationDAL(session).get_active(conversation_id)
    if not conversation:
        raise NotFoundError("Conversation not found")

    project = await ProjectDAL(session).get_by_id(conversation.project_id)
    if not project:
        raise NotFoundError("Project not found")

    rows = await ProjectConversationMessageDAL(session).list_recent_for_conversation(
        conversation_id,
        limit=settings.llm_context_window_messages,
    )

    prompt = (
        project.llm_system_prompt.strip()
        if getattr(project, "llm_system_prompt", None)
        and project.llm_system_prompt.strip()
        else DEFAULT_PROJECT_SYSTEM_PROMPT
    )
    messages: list[dict[str, str]] = [{"role": "system", "content": prompt}]

    for row in rows:
        content = (row.content_text or "").strip()
        if not content:
            continue
        if row.status == row.Status.ERROR:
            continue
        messages.append({"role": row.role, "content": content})

    return ContextBuildResult(
        conversation=conversation,
        project=project,
        messages=messages,
    )
