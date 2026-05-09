import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import BigInteger, ForeignKey, Integer, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class ReadBase(DeclarativeBase):
    """Base for read-only ORM models that map to pre-existing tables."""


class WriteBase(DeclarativeBase):
    """Base for ORM models that correspond to tables we own and create."""


class UserInfo(ReadBase):
    """Read-only view of the existing user_info table — never written to."""

    __tablename__ = "user_info"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger)
    phone_no: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str | None] = mapped_column(Text)
    hashed_password: Mapped[str | None] = mapped_column(Text)
    gmt_create: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    gmt_modified: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    contact_config: Mapped[dict | None] = mapped_column(JSONB)
    ext_info: Mapped[dict | None] = mapped_column(JSONB)
    user_name: Mapped[str | None] = mapped_column(Text)


class UserEntity(WriteBase):
    """Persistent key-value store for long-lived user facts (e.g. preferred currency)."""

    __tablename__ = "user_entity"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger)
    key: Mapped[str] = mapped_column(Text)
    value: Mapped[dict] = mapped_column(JSONB)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True))


class Thread(WriteBase):
    """A conversation thread grouping related interactions for one user."""

    __tablename__ = "thread"

    thread_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[int] = mapped_column(BigInteger)
    summary: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True))


class Interaction(WriteBase):
    """A single message. Either by user or agent response."""

    __tablename__ = "interaction"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    thread_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("thread.thread_id")
    )
    user_id: Mapped[int] = mapped_column(BigInteger)
    role: Mapped[str] = mapped_column(Text)
    message: Mapped[str] = mapped_column(Text)
    intents: Mapped[dict] = mapped_column(JSONB, default=dict)
    entities: Mapped[dict] = mapped_column(JSONB, default=dict)
    result: Mapped[dict] = mapped_column(JSONB, default=dict)
    embedding: Mapped[list | None] = mapped_column(Vector(384))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True))
