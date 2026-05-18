from __future__ import annotations

import anthropic
import structlog

from iagent.api.schemas.reconciliation import (
    ExtractedDocumentContext,
    ReconciliationSuggestRequest,
    ReconciliationSuggestion,
    TransactionCandidate,
)

log = structlog.get_logger(__name__)

_SYSTEM = (
    "You are a bookkeeping reconciliation assistant. "
    "Given an extracted document (vendor, amount, currency, date) and a list of bank transaction candidates, "
    "identify the single best matching bank transaction.\n\n"
    "Rules:\n"
    "- Only suggest a match if you are confident it refers to the same payment.\n"
    "- Consider vendor name similarity, description, amount, and date proximity.\n"
    "- Do NOT decide whether to post or approve — only suggest a match and explain why.\n\n"
    "Respond ONLY with valid JSON (no markdown):\n"
    '{"suggested_bank_transaction_id": "<id>", "confidence_score": 0.0, "reason": "<explanation>"}'
)


class ReconciliationService:
    def __init__(self, client: anthropic.AsyncAnthropic) -> None:
        self._client = client

    async def suggest(self, request: ReconciliationSuggestRequest) -> ReconciliationSuggestion:
        doc = request.extracted_document
        candidates = request.candidate_bank_transactions

        user_message = _build_prompt(doc, candidates)
        log.info("reconciliation_suggest_start", vendor=doc.vendor_name, candidates=len(candidates))

        result = await self._client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=512,
            system=_SYSTEM,
            messages=[{"role": "user", "content": user_message}],
        )

        import json
        text = result.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]

        data = json.loads(text)
        log.info("reconciliation_suggest_done",
                 suggested=data.get("suggested_bank_transaction_id"),
                 confidence=data.get("confidence_score"))

        return ReconciliationSuggestion(
            suggested_bank_transaction_id=data["suggested_bank_transaction_id"],
            confidence_score=float(data["confidence_score"]),
            reason=data["reason"],
        )


def _build_prompt(doc: ExtractedDocumentContext, candidates: list[TransactionCandidate]) -> str:
    lines = [
        "Extracted document:",
        f"  Vendor: {doc.vendor_name}",
        f"  Amount: {doc.amount} {doc.currency}",
        f"  Date: {doc.invoice_date}",
        f"  Raw text: {(doc.raw_text or '')[:300]}",
        "",
        "Bank transaction candidates:",
    ]
    for c in candidates:
        lines.append(
            f"  - id={c.bank_transaction_id}  amount={c.amount} {c.currency}"
            f"  date={c.transaction_date}  description={c.description}"
            f"  counterparty={c.counterparty_name}"
        )
    lines.append("\nWhich candidate best matches the extracted document?")
    return "\n".join(lines)
