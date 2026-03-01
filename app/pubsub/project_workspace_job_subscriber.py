from __future__ import annotations

from typing import Any

from platform_common.constants.pubsub_topics import (
    PROJECT_WORKSPACE_JOBS_TOPIC,
    PROJECT_WORKSPACE_STREAM_TOPIC,
)
from platform_common.db.dal.project_conversation_message_dal import (
    ProjectConversationMessageDAL,
)
from platform_common.db.session import get_session
from platform_common.logging.logging import get_logger
from platform_common.models.event_outbox import EventOutbox
from platform_common.models.project_conversation import ProjectConversation
from platform_common.models.project_conversation_message import ProjectConversationMessage
from platform_common.pubsub.event import PubSubEvent
from platform_common.pubsub.factory import get_publisher, get_subscriber
from platform_common.utils.enums import EventType
from platform_common.utils.time_helpers import get_current_epoch, utcnow

from services.llm import LLMService

logger = get_logger("project_management.project_workspace_job_subscriber")

FRIENDLY_ERROR_PREFIX = "Lucy's tired right now, has to take a nap. Come back later."


def _trim_preview(value: str | None, limit: int = 120) -> str | None:
    if not value:
        return None
    normalized = " ".join(value.strip().split())
    if len(normalized) <= limit:
        return normalized or None
    return f"{normalized[: limit - 1].rstrip()}..."


def _serialize_provider_error(error: Exception) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "type": error.__class__.__name__,
        "message": str(error),
    }

    for attr in ("status_code", "status", "code", "body"):
        value = getattr(error, attr, None)
        if value is not None:
            payload[attr] = value

    response = getattr(error, "response", None)
    if response is not None:
        payload["response"] = (
            response.model_dump()
            if hasattr(response, "model_dump")
            else str(response)
        )

    return payload


def _map_friendly_error_reason(error: Exception) -> str:
    status_code = getattr(error, "status_code", None) or getattr(error, "status", None)
    message = str(error).lower()

    if status_code == 429:
        return "Rate limit reached."
    if (
        "maximum context length" in message
        or "context length" in message
        or "too many tokens" in message
    ):
        return "Too many tokens."
    if status_code == 400:
        return "Bad request."
    return "Unexpected error."


def _compose_friendly_error_message(error: Exception) -> str:
    return f"{FRIENDLY_ERROR_PREFIX} {_map_friendly_error_reason(error)}"


async def _publish_stream_event(
    event_type: EventType,
    *,
    conversation_id: str,
    message_id: str,
    delta: str | None = None,
    friendly_message: str | None = None,
) -> None:
    await get_publisher().publish(
        PROJECT_WORKSPACE_STREAM_TOPIC,
        PubSubEvent(
            event_type=event_type,
            payload={
                "conversation_id": conversation_id,
                "message_id": message_id,
                "delta": delta,
                "friendly_message": friendly_message,
            },
        ),
    )


async def _create_streaming_message(
    *,
    session,
    conversation_id: str,
    project_id: str,
    user_message_id: str,
    provider: str,
    model: str,
) -> ProjectConversationMessage | None:
    message_dal = ProjectConversationMessageDAL(session)
    existing = await message_dal.get_assistant_by_parent_message_id(
        conversation_id=conversation_id,
        parent_message_id=user_message_id,
    )
    if existing:
        logger.info(
            "Skipping duplicate LLM job for conversation=%s parent_message_id=%s existing_message_id=%s status=%s",
            conversation_id,
            user_message_id,
            existing.id,
            existing.status,
        )
        return None

    now_epoch = get_current_epoch()
    conversation = await session.get(ProjectConversation, conversation_id)
    if conversation is None:
        raise RuntimeError(f"Conversation {conversation_id} not found")

    message = ProjectConversationMessage(
        conversation_id=conversation_id,
        project_id=project_id,
        user_id=None,
        role=ProjectConversationMessage.Role.ASSISTANT,
        status=ProjectConversationMessage.Status.STREAMING,
        content_text="",
        parent_message_id=user_message_id,
        provider=provider,
        model=model,
    )
    session.add(message)

    conversation.message_count = int(conversation.message_count or 0) + 1
    conversation.last_message_at = now_epoch
    conversation.updated_at = now_epoch
    session.add(conversation)

    await session.commit()
    await session.refresh(message)
    return message


async def _handle_generate_assistant_response(event: PubSubEvent) -> None:
    payload = event.payload or {}
    conversation_id = str(payload.get("conversation_id") or "").strip()
    project_id = str(payload.get("project_id") or "").strip()
    user_message_id = str(payload.get("user_message_id") or "").strip()

    if not conversation_id or not project_id or not user_message_id:
        logger.warning("Invalid LLM job payload: %r", payload)
        return

    llm_service = LLMService()
    assistant_message_id: str | None = None

    try:
        async for session in get_session():
            request = await llm_service.build_request(
                session=session,
                conversation_id=conversation_id,
            )
            assistant_message = await _create_streaming_message(
                session=session,
                conversation_id=conversation_id,
                project_id=project_id,
                user_message_id=user_message_id,
                provider=request.provider,
                model=request.model,
            )
            if assistant_message is None:
                return
            assistant_message_id = assistant_message.id

            chunks: list[str] = []
            usage_json: dict[str, Any] | None = None

            try:
                async for stream_event in llm_service.stream_chat(request):
                    if stream_event.delta:
                        chunks.append(stream_event.delta)
                        await _publish_stream_event(
                            EventType.PROJECT_ASSISTANT_CHUNK,
                            conversation_id=conversation_id,
                            message_id=assistant_message.id,
                            delta=stream_event.delta,
                        )
                    if stream_event.usage:
                        usage_json = stream_event.usage

                full_text = "".join(chunks)
                now_epoch = get_current_epoch()
                assistant_message.content_text = full_text
                assistant_message.status = ProjectConversationMessage.Status.COMPLETED
                assistant_message.usage_json = usage_json
                assistant_message.updated_at = now_epoch
                session.add(assistant_message)

                conversation = await session.get(ProjectConversation, conversation_id)
                if conversation is not None:
                    conversation.last_message_preview = _trim_preview(full_text)
                    conversation.last_message_at = now_epoch
                    conversation.updated_at = now_epoch
                    session.add(conversation)

                session.add(
                    EventOutbox(
                        entity_type="project_conversation_message",
                        entity_id=assistant_message.id,
                        datastore_id=getattr(request.context.project, "datastore_id", None),
                        old_status=None,
                        new_status="assistant_finalized",
                        payload={
                            "event_name": "project.assistant_message_finalized",
                            "project_id": request.context.project.id,
                            "conversation_id": conversation_id,
                            "message_id": assistant_message.id,
                            "parent_message_id": assistant_message.parent_message_id,
                            "provider": request.provider,
                            "model": request.model,
                            "usage_json": usage_json,
                        },
                        occurred_at=utcnow(),
                    )
                )
                await session.commit()

                await _publish_stream_event(
                    EventType.PROJECT_ASSISTANT_COMPLETED,
                    conversation_id=conversation_id,
                    message_id=assistant_message.id,
                )
            except Exception as error:
                logger.exception(
                    "LLM streaming failed for conversation=%s parent_message_id=%s",
                    conversation_id,
                    user_message_id,
                )
                friendly_message = _compose_friendly_error_message(error)
                now_epoch = get_current_epoch()
                assistant_message.content_text = friendly_message
                assistant_message.status = ProjectConversationMessage.Status.ERROR
                assistant_message.provider_error_json = _serialize_provider_error(error)
                assistant_message.updated_at = now_epoch
                session.add(assistant_message)

                conversation = await session.get(ProjectConversation, conversation_id)
                if conversation is not None:
                    conversation.last_message_preview = friendly_message
                    conversation.last_message_at = now_epoch
                    conversation.updated_at = now_epoch
                    session.add(conversation)

                await session.commit()

                await _publish_stream_event(
                    EventType.PROJECT_ASSISTANT_ERROR,
                    conversation_id=conversation_id,
                    message_id=assistant_message.id,
                    friendly_message=friendly_message,
                )
            break
    except Exception:
        logger.exception(
            "Project workspace LLM job handler crashed for conversation=%s message_id=%s",
            conversation_id,
            assistant_message_id,
        )


async def start_project_workspace_job_subscriber() -> None:
    subscriber = get_subscriber()
    logger.info(
        "Starting Redis subscription for project workspace jobs on topic '%s'",
        PROJECT_WORKSPACE_JOBS_TOPIC,
    )
    await subscriber.subscribe(
        {
            PROJECT_WORKSPACE_JOBS_TOPIC: {
                EventType.GENERATE_ASSISTANT_RESPONSE.value: (
                    _handle_generate_assistant_response
                ),
            }
        }
    )
