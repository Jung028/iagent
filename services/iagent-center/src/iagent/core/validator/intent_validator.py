from typing import Any, Dict

from iagent.core.intent.intent_contract_requirements import INTENT_REQUIREMENTS
from iagent.core.models.intent import Intent
from iagent.core.models.validation import ValidationResult, ValidationStatus


class IntentValidator:

    @staticmethod
    async def validate(intent: str, entities: Dict[str, Any]) -> ValidationResult:
        # READ always passes — the agent decides what to fetch
        if intent == Intent.READ:
            return ValidationResult(
                status=ValidationStatus.READY,
                missing=[],
                cleaned_entities={},
            )

        # Unknown intent (not in requirements) → treat as READ
        if intent not in INTENT_REQUIREMENTS:
            return ValidationResult(
                status=ValidationStatus.READY,
                missing=[],
                cleaned_entities={},
            )

        cleaned = IntentValidator._sanitize(entities)
        missing = [
            f for f in INTENT_REQUIREMENTS[intent]["required"]
            if f not in cleaned or cleaned[f] in (None, "", [])
        ]

        if missing:
            return ValidationResult(
                status=ValidationStatus.INSUFFICIENT_CONTEXT,
                missing=missing,
                question=IntentValidator._build_question(intent, missing),
            )

        return ValidationResult(
            status=ValidationStatus.READY,
            missing=[],
            cleaned_entities=cleaned,
        )

    @staticmethod
    def _sanitize(entities: Dict[str, Any]) -> Dict[str, Any]:
        return {k: v for k, v in entities.items() if v is not None} if entities else {}

    @staticmethod
    def _build_question(intent: str, missing: list) -> str:
        if intent == Intent.TRANSFER and "amount" in missing:
            return "How much would you like to transfer?"
        if intent == Intent.TOP_UP and "amount" in missing:
            return "How much would you like to top up?"
        return "I need a bit more information to proceed."
