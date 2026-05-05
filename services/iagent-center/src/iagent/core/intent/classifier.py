import anthropic
import structlog

from iagent.core.models.intent import Intent, IntentResult
from iagent.core.intent.prompts import EXTRACT_INTENT_TOOL, SYSTEM_PROMPT

log = structlog.get_logger(__name__)

MODEL = "claude-haiku-4-5"   # fast + cheap — ideal for classification


class IntentClassifier:
    """
    LLM-based intent classifier using Claude tool use.
    - Forces tool call via tool_choice={"type": "any"}
    - Safe StrEnum mapping (no ValueError on unknown intent)
    - Redis cache to avoid redundant LLM calls
    """

    def __init__(self, client: anthropic.AsyncAnthropic, redis: object) -> None:
        self._client = client
        self._redis = redis

        # Precompute safe mapping — avoids Intent(value) raising ValueError
        self._intent_map = {intent.value: intent for intent in Intent}

    async def classify(self, user_id: str, message: str) -> IntentResult:
        from iagent.core.intent.cache import get_cached, set_cached

        # 1. cache lookup
        cached = await get_cached(self._redis, user_id, message)
        if cached is not None:
            log.info("intent_cache_hit", user_id=user_id, intent=cached.intent)
            return cached

        # 2. LLM call
        try:
            result = await self._call_llm(message)
        except Exception as exc:
            log.warning("intent_classification_failed", error=str(exc))
            result = IntentResult(intent=Intent.UNKNOWN, confidence=0.0, entities={})

        # 3. cache result
        await set_cached(self._redis, user_id, message, result)

        log.info(
            "intent_classified",
            user_id=user_id,
            intent=result.intent,
            confidence=result.confidence,
        )

        return result

    async def _call_llm(self, message: str) -> IntentResult:
        """Call Claude with forced tool use — always returns structured output."""

        response = await self._client.messages.create(
            model=MODEL,
            max_tokens=512,
            system=SYSTEM_PROMPT,
            tools=[EXTRACT_INTENT_TOOL],
            tool_choice={"type": "any"},   # force a tool call — never plain text
            messages=[{"role": "user", "content": message}],
        )

        # Find the tool_use block in the response
        for block in response.content:
            if block.type == "tool_use" and block.name == "extract_financial_intent":
                return self._build_result(block.input)

        # Should never reach here with tool_choice="any", but safe fallback
        return self._fallback()

    def _build_result(self, args: dict) -> IntentResult:
        """Convert Claude tool output → safe IntentResult."""

        raw_intent = args.get("intent", "unknown")
        normalized = str(raw_intent).lower().strip()

        # Safe enum lookup — falls back to UNKNOWN if LLM returns unexpected value
        intent = self._intent_map.get(normalized, Intent.UNKNOWN)

        try:
            confidence = float(args.get("confidence", 0.0))
        except Exception:
            confidence = 0.0

        return IntentResult(
            intent=intent,
            confidence=confidence,
            entities=dict(args.get("entities", {})),
        )

    def _fallback(self) -> IntentResult:
        return IntentResult(intent=Intent.UNKNOWN, confidence=0.0, entities={})
