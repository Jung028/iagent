# This file holds the two constants we send to Claude (the LLM) on every request.
# Keeping them here (separate from the classifier logic) makes them easy to find and edit.

# SYSTEM_PROMPT is the instruction we give Claude once, at the start of every conversation.
# It defines Claude's role and constraints. The "cache_control" we attach to it in classifier.py
# tells the Anthropic API to cache this text server-side, so we're not charged tokens for
# re-sending the same system prompt on every request.
#
# The triple-quoted string """ ... """ is Python's multi-line string — like Java's text blocks:
# String text = """
#     line one
#     line two
# """;
#
# The backslash \ at the end of the first line prevents a leading newline in the string.
SYSTEM_PROMPT = """\
You are the intent classification engine for iAgent Center, the AI layer of an eWallet platform.
Your only job is to call the extract_financial_intent tool with structured data from the user's message.

Never respond with plain text. Always call the tool.

Supported intents:
- balance_inquiry: user wants to know their balance or account info
- unknown: message does not match a supported intent
"""

# EXTRACT_INTENT_TOOL is the "tool definition" we give to Claude.
# Claude's tool_use feature is like giving it a function signature and JSON schema,
# and telling it to fill in the arguments based on the user's message.
# Instead of responding with free text, Claude MUST call this tool with structured JSON.
#
# WHY: We never want to parse free text from an LLM. Structured output (via tool_use)
# is reliable, type-safe, and can be validated — free text cannot.
#
# dict[str, Any] means: a dictionary where keys are strings and values can be anything.
# In Java: Map<String, Object>
EXTRACT_INTENT_TOOL: dict = {
    # "name" is what Claude calls when it uses this tool — we match this name in classifier.py
    "name": "extract_financial_intent",

    # "description" helps Claude understand WHEN to use this tool.
    "description": "Extract the user's financial intent from their message.",

    # "input_schema" is a JSON Schema that defines the structure Claude must return.
    # This is like defining method parameters in Java — Claude must provide these fields.
    "input_schema": {
        "type": "object",
        "properties": {
            "intent": {
                "type": "string",
                # "enum" restricts the value to one of these exact strings only.
                # Claude cannot return any other value for "intent".
                "enum": ["balance_inquiry", "unknown"],
            },
            "confidence": {
                "type": "number",
                "description": "Confidence score between 0 and 1",
            },
        },
        # "required" lists the fields Claude MUST always provide (cannot be omitted).
        "required": ["intent", "confidence"],
    },
}
