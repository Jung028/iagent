from typing import Any
from pydantic import BaseModel


class DocumentExtractRequest(BaseModel):
    source_document_id: str
    file_url: str
    mime_type: str
    metadata: dict[str, Any] = {}


class ExtractedFields(BaseModel):
    vendor: str | None = None
    date: str | None = None
    amount: float | None = None
    currency: str | None = None
    category: str | None = None
    description: str | None = None


class DocumentExtractResponse(BaseModel):
    source_document_id: str
    status: str  # "success" | "partial" | "failed"
    extracted: ExtractedFields
    missing_fields: list[str]
    clarifying_questions: list[str]
    raw_text: str | None = None
