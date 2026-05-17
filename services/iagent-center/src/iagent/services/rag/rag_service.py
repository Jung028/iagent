import asyncio
import json
import uuid
from typing import Any

import anthropic
from iagent.core.context.service_context import ServiceContext
from sentence_transformers import SentenceTransformer
import structlog
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from iagent.integrations.iuser import IUserClient

from .repositories import (
    InteractionRepository,
    ThreadRepository,
    UserEntityRepository,
)

log = structlog.get_logger(__name__)

_SUMMARY_MODEL = "claude-haiku-4-5"
_SUMMARY_SYSTEM = """\
You are a summarisation assistant. Given a list of conversation turns from an eWallet chatbot, \
write ONE concise paragraph (2-4 sentences) describing what happened: what the user asked for, \
what actions were taken, and any relevant outcomes (balances, transaction IDs, etc.). \
Plain text only — no markdown, no bullet points.
"""


async def _noop() -> None:
    return None


class RAGService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        redis: Any,
        user_client: IUserClient,
        anthropic_client: anthropic.AsyncAnthropic | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._redis = redis
        self._user_client = user_client
        self._anthropic = anthropic_client
        self._model = SentenceTransformer("all-MiniLM-L6-v2")

    """
    Get the context for the RAG agent to pass in during chat in ctx. 
    """
    async def get_context(
        self,
        user_id: str,
        message: str,
        thread_id: str | None = None,
        service_ctx: ServiceContext | None = None,   
    ) -> dict:
        int_user_id = _parse_user_id(user_id)
        uuid_thread_id = _parse_uuid(thread_id)

        ctx_kwargs = service_ctx.to_kwargs() if service_ctx else {}
        phone_no = service_ctx.phone_no if service_ctx else None


        profile = None
        entities_list: list = []
        thread = None
        recent_messages: list = []

        if int_user_id is not None:
            async with self._session_factory() as session:
                entity_repo = UserEntityRepository(session)
                thread_repo = ThreadRepository(session)
                interaction_repo = InteractionRepository(session)

                results = await asyncio.gather(
                    self._user_client.query_user_info(user_id, phone_no=phone_no, **ctx_kwargs),
                    entity_repo.query_user_entity_by_user_id(int_user_id),
                    thread_repo.query_by_thread_id(uuid_thread_id) if uuid_thread_id else _noop(),
                    interaction_repo.query_recent_interaction_by_thread(uuid_thread_id) if uuid_thread_id else _noop(),
                    return_exceptions=True,
                )

            # Unpack results — treat any exception as a missing value and log it.
            if isinstance(results[0], Exception):
                log.warning("rag.user_info_failed", user_id=user_id, error=str(results[0]))
            profile = results[0] if not isinstance(results[0], Exception) else None
            entities_list = results[1] if not isinstance(results[1], Exception) else []
            thread = results[2] if not isinstance(results[2], Exception) else None
            raw_recent = results[3] if not isinstance(results[3], Exception) else []
            recent_messages = [{"role": m.role, "content": m.message} for m in (raw_recent or [])]

            print(thread)


        # Semantic search — runs AFTER the session is closed so we don't hold a DB
        # connection open during the OpenAI embedding API call.
        relevant_history: list = []
        if int_user_id is not None and message:
            try:
                embedding = await self._get_embedding(message)
                async with self._session_factory() as session:
                    similar_interactions = await InteractionRepository(session).query_similar_interactions(int_user_id, embedding)
                relevant_history = [{"role": i.role, "content": i.message} for i in similar_interactions]
            except Exception as exc:
                log.warning("rag.embedding_failed", user_id=user_id, error=str(exc))

        session_data: dict = {}
        try:
            cached = await self._redis.get(f"session:{user_id}")
            if cached:
                session_data = json.loads(cached)
        except Exception as exc:
            log.warning("rag.redis_read_failed", user_id=user_id, error=str(exc))

        return {
            "profile": profile,
            "entities": {e.key: e.value for e in entities_list},
            "thread_id": str(thread.thread_id) if thread else (thread_id or ""),
            "thread_summary": thread.summary if thread else None,
            "recent_messages": recent_messages,
            "relevant_history": relevant_history,
            "session": session_data,
        }

    """
    Store the interaction in the database and cache the thread_id in redis 
    for quick retrieval in 1 hour session. 
    """
    async def store(
        self,
        user_id: str,
        thread_id: str,
        message: str,
        intents: Any,
        entities: dict,
        result: Any,
    ) -> None:
        """Never raises — errors are logged silently so the user response is never blocked."""
        int_user_id = _parse_user_id(user_id)
        if int_user_id is None:
            log.warning("rag.store_skipped_invalid_user_id", user_id=user_id)
            return

        uuid_thread_id = _parse_uuid(thread_id)
        thread_obj = None

        try:
            # Get embedding BEFORE opening the DB session to avoid holding it open during the API call
            try:
                embedding = await self._get_embedding(message)
            except Exception as exc:
                log.warning("rag.embedding_skipped", user_id=user_id, error=str(exc))
                embedding = None

            async with self._session_factory() as session:
                async with session.begin():
                    thread_repo = ThreadRepository(session)
                    entity_repo = UserEntityRepository(session)
                    interaction_repo = InteractionRepository(session)

                    if uuid_thread_id:
                        thread_obj = await thread_repo.query_by_thread_id(uuid_thread_id)
                    if thread_obj is None:
                        thread_obj = await thread_repo.create_new_thread(int_user_id)

                    await interaction_repo.save_user_interaction(
                        thread_id=thread_obj.thread_id,
                        user_id=int_user_id,
                        message=message,
                        intents=intents,
                        entities=entities,
                        embedding=embedding,
                    )
                    await interaction_repo.save_assistant_interaction(
                        thread_id=thread_obj.thread_id,
                        user_id=int_user_id,
                        result=result,
                    )
                    if entities:
                        await entity_repo.insert_or_update_entities(int_user_id, entities)
                    await thread_repo.update_time_modified(thread_obj.thread_id)

            if thread_obj:
                try:
                    await self._redis.setex(
                        f"session:{user_id}",
                        3600,
                        json.dumps({"thread_id": str(thread_obj.thread_id)}),
                    )
                except Exception as exc:
                    log.warning("rag.redis_write_failed", user_id=user_id, error=str(exc))

                # Generate and persist a fresh summary in the background.
                if self._anthropic:
                    asyncio.create_task(
                        self._refresh_summary(thread_obj.thread_id)
                    )

        except Exception as exc:
            log.error("rag.store_failed", user_id=user_id, error=str(exc))

    # ── Thread listing & detail ───────────────────────────────────────────────

    async def list_threads(self, user_id: str) -> list[dict]:
        """Return all threads for a user ordered by most recently modified."""
        int_user_id = _parse_user_id(user_id)
        if int_user_id is None:
            return []
        async with self._session_factory() as session:
            threads = await ThreadRepository(session).query_by_user_id(int_user_id)
        return [
            {
                "thread_id":  str(t.thread_id),
                "summary":    t.summary,
                "created_at": t.created_at,
                "updated_at": t.updated_at,
            }
            for t in threads
        ]

    async def get_thread_detail(self, thread_id: str) -> dict:
        """Return a thread's metadata + all interactions ordered oldest → newest."""
        uuid_thread_id = _parse_uuid(thread_id)
        if uuid_thread_id is None:
            return {"thread_id": thread_id, "summary": None, "interactions": []}

        async with self._session_factory() as session:
            thread, interactions = await asyncio.gather(
                ThreadRepository(session).query_by_thread_id(uuid_thread_id),
                InteractionRepository(session).query_all_by_thread(uuid_thread_id),
            )

        return {
            "thread_id":    thread_id,
            "summary":      thread.summary if thread else None,
            "interactions": [
                {
                    "id":         str(i.id),
                    "role":       i.role,
                    "message":    i.message or None,
                    "result":     i.result or None,
                    "created_at": i.created_at,
                }
                for i in interactions
            ],
        }

    # ── Summary generation ────────────────────────────────────────────────────

    async def _refresh_summary(self, thread_id: uuid.UUID) -> None:
        """Generate a plain-text summary of the thread and persist it. Fire-and-forget."""
        try:
            async with self._session_factory() as session:
                interactions = await InteractionRepository(session).query_all_by_thread(thread_id)

            if not interactions:
                return

            # Build a compact conversation transcript for Claude
            lines = []
            for i in interactions:
                if i.role == "user" and i.message:
                    lines.append(f"User: {i.message}")
                elif i.role == "assistant":
                    result = i.result or {}
                    ui = result.get("ui", result)
                    summary = ui.get("summary") if isinstance(ui, dict) else None
                    if summary:
                        lines.append(f"Assistant: {summary}")

            if not lines:
                return

            transcript = "\n".join(lines[-20:])  # last 20 turns max

            response = await self._anthropic.messages.create(
                model=_SUMMARY_MODEL,
                max_tokens=256,
                system=_SUMMARY_SYSTEM,
                messages=[{"role": "user", "content": transcript}],
            )
            summary_text = next(
                (b.text for b in response.content if hasattr(b, "text")), ""
            ).strip()

            if summary_text:
                async with self._session_factory() as session:
                    async with session.begin():
                        await ThreadRepository(session).update_summary(thread_id, summary_text)
                log.info("rag.summary_updated", thread_id=str(thread_id))

        except Exception as exc:
            log.warning("rag.summary_failed", thread_id=str(thread_id), error=str(exc))

    async def _get_embedding(self, text: str) -> list[float]:
        # SentenceTransformer is synchronous — run in thread pool so it
        # doesn't block the async event loop
        loop = asyncio.get_event_loop()
        embedding = await loop.run_in_executor(
            None, self._model.encode, text
        )
        return embedding.tolist()


def _parse_user_id(user_id: str) -> int | None:
    try:
        return int(user_id)
    except (ValueError, TypeError):
        return None


def _parse_uuid(value: str | None) -> uuid.UUID | None:
    if not value:
        return None
    try:
        return uuid.UUID(value)
    except ValueError:
        return None
