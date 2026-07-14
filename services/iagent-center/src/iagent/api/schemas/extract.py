from typing import Any
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class DocumentExtractRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    source_document_id: str
    file_url: str
    mime_type: str
    metadata: dict[str, Any] = {}


class ReceiptLineItem(BaseModel):
    name: str
    quantity: int = 1
    unit_price: float


class ExtractedFields(BaseModel):
    vendor: str | None = None
    date: str | None = None
    amount: float | None = None
    currency: str | None = None
    category: str | None = None
    description: str | None = None
    tax_amount: float | None = None
    sst_amount: float | None = None
    items: list[ReceiptLineItem] = []


class DocumentExtractResponse(BaseModel):
    source_document_id: str
    status: str  # "success" | "partial" | "failed"
    extracted: ExtractedFields
    missing_fields: list[str]
    clarifying_questions: list[str]
    raw_text: str | None = None
