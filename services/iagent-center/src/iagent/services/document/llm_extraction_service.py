import json

import anthropic
import structlog

log = structlog.get_logger(__name__)

_SYSTEM = (
    "You are a bookkeeping assistant. Given raw text from a receipt or document, extract:\n"
    "- vendor: merchant/business name\n"
    "- date: transaction date in YYYY-MM-DD format\n"
    "- amount: total amount as a decimal number\n"
    "- currency: 3-letter currency code (default SGD if not visible)\n"
    "- category: exactly one of [GROCERIES, FOOD_DINING, TRANSPORT, FUEL, SHOPPING, "
    "ENTERTAINMENT, UTILITIES, RENT, HEALTHCARE, EDUCATION, TRANSFER, TOP_UP, OTHER]\n"
    "- description: brief description, max 60 chars\n"
    "- tax_amount: any generic tax line shown on the receipt (GST, service tax, VAT, etc.) "
    "that is not specifically labelled SST, as a decimal number. 0 if none shown.\n"
    "- sst_amount: the amount specifically labelled SST (Sales and Service Tax), as a decimal "
    "number. 0 if none shown. If a tax line's label is ambiguous, put it in tax_amount instead.\n"
    "- items: array of individual line items from the receipt, each with "
    "{\"name\": str, \"quantity\": int, \"unit_price\": float}. "
    "Extract every distinct item. If quantity is not shown assume 1.\n\n"
    "Rules: only fill fields you are CERTAIN about. Set uncertain/missing fields to null "
    "and list them in missing_fields with a clarifying question for each.\n\n"
    "Respond ONLY with valid JSON (no markdown):\n"
    '{"extracted":{"vendor":null,"date":null,"amount":null,"currency":null,'
    '"category":null,"description":null,"tax_amount":null,"sst_amount":null,'
    '"items":[]},"missing_fields":[],"clarifying_questions":[]}'
)


class LLMExtractionService:
    def __init__(self, client: anthropic.AsyncAnthropic) -> None:
        self._client = client

    async def extract_structured_fields(self, raw_text: str) -> dict:
        result = await self._client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=1024,
            system=_SYSTEM,
            messages=[{"role": "user", "content": f"Raw text:\n{raw_text}"}],
        )
        text = result.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text)
