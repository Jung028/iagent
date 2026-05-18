from __future__ import annotations

from pydantic import BaseModel


class TransactionCandidate(BaseModel):
    bank_transaction_id: str
    amount: float
    currency: str
    transaction_date: str | None = None
    description: str | None = None
    counterparty_name: str | None = None


class ExtractedDocumentContext(BaseModel):
    vendor_name: str | None = None
    amount: float | None = None
    currency: str | None = None
    invoice_date: str | None = None
    raw_text: str | None = None


class ReconciliationSuggestRequest(BaseModel):
    extracted_document: ExtractedDocumentContext
    candidate_bank_transactions: list[TransactionCandidate]


class ReconciliationSuggestion(BaseModel):
    suggested_bank_transaction_id: str
    confidence_score: float
    reason: str
