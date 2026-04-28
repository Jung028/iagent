import json
from dataclasses import dataclass
from datetime import datetime, timezone

import structlog
from google import genai
from google.genai import types

log = structlog.get_logger(__name__)

_SUMMARY_PROMPT = """\
You are a financial assistant summarising analysis results for a user.

The user asked: "{question}"

Computed results (JSON):
{results}

Write a single, natural, conversational response that directly answers the user.
Be specific with numbers and currency. Do not use bullet points or headers.
If survival_forecast is present, give an honest assessment.
"""


@dataclass
class AnalysisResult:
    count: int | None = None
    average: float | None = None
    total: float | None = None
    currency: str = "MYR"
    survival_forecast: str | None = None
    summary: str = ""


class TransactionAnalyzer:
    """Executes an analysis plan against a list of transactions.

    This is the RAG augmented-generation step:
    - Retrieval already happened (iWallet returned transactions)
    - We inject those transactions as context into the LLM for the summary
    - Python handles the deterministic maths (count, average, total)
    - LLM handles the natural language summary and forecast reasoning
    """

    def __init__(self, client: genai.Client) -> None:
        self._client = client

    async def analyze(
        self,
        question: str,
        transactions: list[dict],
        plan: list[dict],
    ) -> AnalysisResult:
        result = AnalysisResult()
        result.currency = transactions[0].get("currency", "MYR") if transactions else "MYR"

        for task in plan:
            op = task.get("op")
            filtered = self._apply_filter(transactions, task.get("filter"))
            field = task.get("field", "amount")

            if op == "count":
                result.count = len(filtered)

            elif op == "average":
                values = [t.get(field) for t in filtered if t.get(field) is not None]
                result.average = round(sum(values) / len(values), 2) if values else 0.0

            elif op == "total":
                values = [t.get(field) for t in filtered if t.get(field) is not None]
                result.total = round(sum(values), 2)

            elif op == "survival_forecast":
                result.survival_forecast = self._estimate_forecast(transactions)

        result.summary = await self._summarize(question, result)
        return result

    def _apply_filter(self, transactions: list[dict], filter_spec: dict | None) -> list[dict]:
        if not filter_spec:
            return transactions
        field = filter_spec.get("field", "amount")
        if "lt" in filter_spec:
            return [t for t in transactions if (t.get(field) or 0) < filter_spec["lt"]]
        if "gt" in filter_spec:
            return [t for t in transactions if (t.get(field) or 0) > filter_spec["gt"]]
        return transactions

    def _estimate_forecast(self, transactions: list[dict]) -> str:
        if not transactions:
            return "No transaction data available to estimate weekly spend."
        amounts = [t.get("amount") or 0 for t in transactions]
        avg_per_txn = sum(amounts) / len(amounts)
        today = datetime.now(tz=timezone.utc)
        days_left = 7 - today.weekday()  # weekday(): Mon=0, Sun=6
        projected = round(avg_per_txn * len(amounts) / 7 * days_left, 2)
        return (
            f"Based on {len(amounts)} transactions averaging {avg_per_txn:.2f}, "
            f"projected spend for the remaining {days_left} day(s) this week is ~{projected:.2f}."
        )

    async def _summarize(self, question: str, result: AnalysisResult) -> str:
        results_text = json.dumps(
            {
                "count": result.count,
                "average": result.average,
                "total": result.total,
                "currency": result.currency,
                "survival_forecast": result.survival_forecast,
            },
            indent=2,
        )
        try:
            response = await self._client.aio.models.generate_content(
                model="gemini-2.5-flash",
                contents=_SUMMARY_PROMPT.format(
                    question=question,
                    results=results_text,
                ),
            )
            return response.text.strip()
        except Exception as exc:
            log.warning("analysis_summary_failed", error=str(exc))
            parts = []
            if result.count is not None:
                parts.append(f"{result.count} transactions found")
            if result.average is not None:
                parts.append(f"average {result.average} {result.currency}")
            if result.total is not None:
                parts.append(f"total {result.total} {result.currency}")
            return ". ".join(parts) or "Analysis complete."
