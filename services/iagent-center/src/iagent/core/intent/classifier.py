import structlog  # Structured logging library — produces JSON log lines instead of plain text

import anthropic   # The official Anthropic Python SDK for calling Claude

from iagent.core.intent.models import Intent, IntentResult
from iagent.core.intent.prompts import EXTRACT_INTENT_TOOL, SYSTEM_PROMPT

# "structlog.get_logger(__name__)" creates a logger named after this module's path.
# "__name__" is a built-in Python variable that holds the current module's name
# (e.g. "iagent.core.intent.classifier"). This is like LoggerFactory.getLogger(getClass()) in Java.
log = structlog.get_logger(__name__)

# A module-level constant for the Claude model name we use for classification.
# Declaring it here (not inside the class) makes it easy to change in one place.
MODEL = "claude-sonnet-4-5"


class IntentClassifier:
    """Classifies a user's natural language message into a structured Intent.

    This is the only place in the codebase that calls the Anthropic (Claude) API.
    It uses a Redis cache to avoid redundant LLM calls for repeated messages.
    """

    # "__init__" is Python's constructor — equivalent to Java's public IntentClassifier(...) {}
    # "self" is Python's equivalent of Java's "this" — it refers to the current instance.
    # You MUST include "self" as the first parameter of every instance method in Python.
    # In Java it's implicit; in Python you must be explicit.
    def __init__(self, client: anthropic.AsyncAnthropic, redis: object) -> None:
        # "self._client" stores the parameter as an instance variable.
        # The underscore prefix (_) is convention for "private" — like Java's private field.
        # In Java: private final AsyncAnthropic client;  this.client = client;
        self._client = client
        self._redis = redis

    async def classify(self, user_id: str, message: str) -> IntentResult:
        """Public method: classify a message, using cache when available.

        This is the method called by the route handler in chat.py.
        It always returns an IntentResult — it never raises an exception to the caller.
        If the LLM call fails, it returns UNKNOWN instead of crashing.
        """
        #1. Try search cache if user has already asked same question to get intent, return intent,
        #2. else, it will call_llm, which basically, retrieves the intent "balance_inquiry"
        #3. then set_cached for future reference. in case user asks the same question, we can retrieve intent again. 

        # Import cache functions inside the method to avoid a circular import issue.
        # (cache.py imports from models.py; models.py doesn't import cache.py — fine.
        # But if both were imported at the top of this file, Python might try to import
        # them before they're fully loaded.) This is a Python-specific concern.
        from iagent.core.intent.cache import get_cached, set_cached

        # Try the cache first. If we already classified this exact message for this user
        # within the last 5 minutes, return the cached result immediately (no LLM call).
        cached = await get_cached(self._redis, user_id, message)
        if cached is not None:
            # "log.info()" logs a structured JSON line. The keyword arguments (user_id=, intent=)
            # become fields in the JSON log output — easy to query in a log management tool.
            log.info("intent_cache_hit", user_id=user_id, intent=cached.intent)
            return cached

        # Cache miss — we need to call the LLM.
        # "try/except" is Python's equivalent of Java's try/catch.
        try:
            result = await self._call_llm(message)
        except Exception as exc:
            # "Exception" is the base class for all exceptions in Python (like Java's Exception).
            # "as exc" binds the exception to the variable "exc" so we can read its message.
            # If the Anthropic API is down or times out, we fall back to UNKNOWN
            # rather than returning a 500 error to the user.
            log.warning("intent_classification_failed", error=str(exc))
            result = IntentResult(intent=Intent.UNKNOWN, confidence=0.0)

        # Store the result in cache (even UNKNOWN — no point retrying a bad message for 5 min).
        await set_cached(self._redis, user_id, message, result)
        log.info("intent_classified", user_id=user_id, intent=result.intent)
        return result

    async def _call_llm(self, message: str) -> IntentResult:
        """Private method: make the actual Anthropic API call.

        The leading underscore signals this is internal — only called by classify().
        In Java this would be: private IntentResult callLlm(String message)
        """

        # "block.input" is the dict Claude filled in according to our JSON schema.
                # e.g. {"intent": "balance_inquiry", "confidence": 0.97}
        #4. 

        # Call the Anthropic Messages API.
        # "await" is needed because this is a network call — it pauses execution here
        # and lets other requests be processed while waiting for the API response.
        response = await self._client.messages.create(
            model=MODEL,
            max_tokens=128,  # Cap the response length — we only need a short JSON tool call

            # "system" sets the persistent instructions for Claude.
            # We pass it as a list with one dict so we can attach "cache_control".
            # "cache_control: {"type": "ephemeral"}" tells Anthropic's servers to cache
            # this system prompt — we're not re-charged tokens for it on repeat calls.
            system=[
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],

            # "tools" is the list of tool definitions Claude can call.
            # We pass only one tool, so Claude is forced to call it.
            # The "# type: ignore[list-item]" suppresses a mypy type mismatch warning
            # caused by our dict not matching the SDK's exact TypedDict shape — safe to ignore.
            tools=[EXTRACT_INTENT_TOOL],  # type: ignore[list-item]

            # "tool_choice: {"type": "any"}" tells Claude it MUST call one of the tools.
            # Without this, Claude might sometimes respond with text instead of a tool call.
            tool_choice={"type": "any"},

            # "messages" is the conversation history. For classification we only send
            # the current user message — no previous turns needed.
            messages=[{"role": "user", "content": message}],
        )

        # Claude's response contains a list of "content blocks".
        # When Claude uses a tool, one block will be of type "tool_use".
        # We loop through all blocks looking for the one we care about.
        #
        # "for X in Y:" is Python's for-each loop — like Java's "for (X x : y)"
        for block in response.content:

            # Check if this block is a tool call AND it's the right tool name.
            if block.type == "tool_use" and block.name == "extract_financial_intent":

                # "block.input" is the dict Claude filled in according to our JSON schema.
                # e.g. {"intent": "balance_inquiry", "confidence": 0.97}
                inp = block.input  # type: ignore[attr-defined]

                return IntentResult(
                    # Intent(inp["intent"]) converts the string to our Intent enum.
                    # inp["intent"] reads the "intent" key from the dict — like Java's Map.get().
                    intent=Intent(inp["intent"]),

                    # .get("confidence", 1.0) returns the value or 1.0 if the key is missing.
                    # In Java: (double) inp.getOrDefault("confidence", 1.0)
                    confidence=inp.get("confidence", 1.0),
                )

        # If Claude returned no tool_use block (shouldn't happen with tool_choice="any"),
        # fall back to UNKNOWN safely.
        return IntentResult(intent=Intent.UNKNOWN, confidence=0.0)
