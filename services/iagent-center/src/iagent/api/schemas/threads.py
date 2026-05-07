from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ThreadSummary(BaseModel):
    thread_id: str
    summary: str | None = None
    created_at: datetime
    updated_at: datetime


class ThreadListResponse(BaseModel):
    threads: list[ThreadSummary]


class InteractionItem(BaseModel):
    id: str
    role: str
    message: str | None = None
    result: dict[str, Any] | None = None
    created_at: datetime


class ThreadDetailResponse(BaseModel):
    thread_id: str
    summary: str | None = None
    interactions: list[InteractionItem]
