import dataclasses
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Interaction, Thread, UserEntity, UserInfo


def _to_jsonable(val: Any) -> Any:
    if val is None:
        return {}
    if isinstance(val, (dict, list, str, int, float, bool)):
        return val
    if hasattr(val, "model_dump"):
        return val.model_dump()
    if dataclasses.is_dataclass(val) and not isinstance(val, type):
        return dataclasses.asdict(val)
    return str(val)



class UserEntityRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def query_user_entity_by_user_id(self, user_id: int) -> list[UserEntity]:
        result = await self._session.execute(
            select(UserEntity).where(UserEntity.user_id == user_id)
        )
        return list(result.scalars().all())

    # if a key exists, update, else insert a new row, this is to ensure that 
    """

    Example: 
    
    entities={
        "currency": "AUD",
        "budget_limit": 2000,
        "preferred_category": "food"
    }


    becomes: 


    [
        {
            "user_id": 1,
            "key": "currency",
            "value": "AUD",
            "updated_at": "2026-05-03T17:00:00Z"
        },
        {
            "user_id": 1,
            "key": "budget_limit",
            "value": 2000,
            "updated_at": "2026-05-03T17:00:00Z"
        },
        {
            "user_id": 1,
            "key": "preferred_category",
            "value": "food",
            "updated_at": "2026-05-03T17:00:00Z"
        }
    ]

    """
    async def insert_or_update_entities(self, user_id: int, entities: dict[str, Any]) -> None:
        if not entities:
            return
        now = datetime.now(UTC)
        # for each of the items in the entities, key and value, for each, create a new row.
        rows = [{"user_id": user_id, "key": k, "value": v, "updated_at": now} for k, v in entities.items()]
        # it will try insert, if on_conflict, it will continue to update value and updated_at time.
        stmt = insert(UserEntity).values(rows)
        await self._session.execute(
            # if a key exists, update the elements value and update_at. 
            stmt.on_conflict_do_update(
                index_elements=["user_id", "key"],
                set_={"value": stmt.excluded.value, "updated_at": stmt.excluded.updated_at},
            )
        )

class ThreadRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def query_by_thread_id(self, thread_id: uuid.UUID) -> Thread | None:
        result = await self._session.execute(
            select(Thread).where(Thread.thread_id == thread_id)
        )
        return result.scalar_one_or_none()

    async def query_by_user_id(self, user_id: int, limit: int = 50) -> list[Thread]:
        """All threads for a user, most recently modified first."""
        result = await self._session.execute(
            select(Thread)
            .where(Thread.user_id == user_id)
            .order_by(Thread.updated_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def create_new_thread(self, user_id: int) -> Thread:
        now = datetime.now(UTC)
        thread = Thread(
            thread_id=uuid.uuid4(),
            user_id=user_id,
            created_at=now,
            updated_at=now,
        )
        self._session.add(thread)
        await self._session.flush()
        return thread

    async def update_time_modified(self, thread_id: uuid.UUID) -> None:
        await self._session.execute(
            update(Thread)
            .where(Thread.thread_id == thread_id)
            .values(updated_at=datetime.now(UTC))
        )

    async def update_summary(self, thread_id: uuid.UUID, summary: str) -> None:
        """Persist a generated summary string for this thread."""
        await self._session.execute(
            update(Thread)
            .where(Thread.thread_id == thread_id)
            .values(summary=summary)
        )


class InteractionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def query_recent_interaction_by_thread(
        self, thread_id: uuid.UUID, limit: int = 10
    ) -> list[Interaction]:
        result = await self._session.execute(
            select(Interaction)
            .where(Interaction.thread_id == thread_id)
            .order_by(Interaction.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def query_all_by_thread(self, thread_id: uuid.UUID) -> list[Interaction]:
        """Full ordered history for a thread — oldest first, newest at bottom."""
        result = await self._session.execute(
            select(Interaction)
            .where(Interaction.thread_id == thread_id)
            .order_by(Interaction.created_at.asc())
        )
        return list(result.scalars().all())

    async def query_similar_interactions(
        self, user_id: int, embedding: list[float], limit: int = 5
    ) -> list[Interaction]:
        result = await self._session.execute(
            select(Interaction)
            .where(Interaction.user_id == user_id)
            .where(Interaction.embedding.isnot(None))
            .order_by(Interaction.embedding.op("<=>")(embedding))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def save_user_interaction(
        self,
        thread_id: uuid.UUID,
        user_id: int,
        message: str,
        intents: Any,
        entities: dict,
        embedding: list[float] | None,
    ) -> None:
        self._session.add(Interaction(
            id=uuid.uuid4(),
            thread_id=thread_id,
            user_id=user_id,
            role="user",
            message=message,
            intents=_to_jsonable(intents),
            entities=entities or {},
            result={},
            embedding=embedding,
            created_at=datetime.now(UTC),
        ))

    async def save_assistant_interaction(
        self,
        thread_id: uuid.UUID,
        user_id: int,
        result: Any,
        message: str = "",
    ) -> None:
        self._session.add(Interaction(
            id=uuid.uuid4(),
            thread_id=thread_id,
            user_id=user_id,
            role="assistant",
            message=message,
            intents={},
            entities={},
            result=_to_jsonable(result),
            embedding=None,
            created_at=datetime.now(UTC),
        ))
