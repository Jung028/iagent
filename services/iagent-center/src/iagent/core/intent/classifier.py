import structlog
from google import genai
from google.genai import types

from iagent.core.models.intent import Intent, IntentResult
from iagent.core.intent.prompts import EXTRACT_INTENT_TOOL, SYSTEM_PROMPT

log = structlog.get_logger(__name__)

MODEL = "gemini-2.5-flash"


class IntentClassifier:
    """
    LLM-based intent classifier with:
    - safe StrEnum mapping
    - cache support
    - robust tool-call parsing
    - router-safe UNKNOWN fallback
    """

    def __init__(self, client: genai.Client, redis: object) -> None:
        self._client = client
        self._redis = redis

        # Precompute safe mapping (fast + avoids Enum(ValueError))
        self._intent_map = {intent.value: intent for intent in Intent}

    async def classify(self, user_id: str, message: str) -> IntentResult:
        from iagent.core.intent.cache import get_cached, set_cached

        # 1. cache lookup (only safe hits)
        cached = await get_cached(self._redis, user_id, message)
        if cached is not None and cached.intent != Intent.UNKNOWN:
            log.info("intent_cache_hit", user_id=user_id, intent=cached.intent)
            return cached

        # 2. LLM call
        try:
            # result = IntentResult(
            #     intent=Intent.BALANCE_INQUIRY,
            #     confidence=0.0,
            #     entities={}
            # )
            result = IntentResult(
                intent=Intent.TRANSACTION_ANALYZE,
                confidence=0.0,
                entities={"time_range":"02/22/12","metric":"009"}
            )
            # TODO: FOR debug purposes, we will hard code the LLM call result. 
            #result = await self._call_llm(message)
        except Exception as exc:
            log.warning("intent_classification_failed", error=str(exc))
            result = IntentResult(
                intent=Intent.UNKNOWN,
                confidence=0.0,
                entities={}
            )

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
        """Call Gemini with safe tool-calling (AUTO mode)."""

        response = await self._client.aio.models.generate_content(
            model=MODEL,
            contents=message,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                tools=[EXTRACT_INTENT_TOOL],
                tool_config=types.ToolConfig(
                    function_calling_config=types.FunctionCallingConfig(
                        mode="AUTO"   # correct supported mode
                    )
                ),
            ),
        )

        # 1. validate response structure
        if not response.candidates:
            return self._fallback()

        candidate = response.candidates[0]

        if not candidate.content or not candidate.content.parts:
            return self._fallback()

        # 2. extract function call
        for part in candidate.content.parts:
            fc = getattr(part, "function_call", None)
            if not fc:
                continue

            if fc.name != "extract_financial_intent":
                continue

            args = dict(fc.args or {})

            return self._build_result(args)

        # 3. no tool call returned
        return self._fallback()

    def _build_result(self, args: dict) -> IntentResult:
        """Convert LLM output → safe IntentResult.
        We retrieve the enties from the llm, identifying the relevant context 
        """

        raw_intent = args.get("intent", "unknown")

        # normalize LLM output (critical fix)
        normalized = str(raw_intent).lower().strip()

        # safe enum mapping (NO direct Enum(value) casting)
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
        """Safe fallback when LLM fails."""
        return IntentResult(
            intent=Intent.UNKNOWN,
            confidence=0.0,
            entities={}
        )