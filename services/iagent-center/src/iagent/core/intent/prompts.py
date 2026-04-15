from google.genai import types

SYSTEM_PROMPT = """\
You are the intent classification engine for iAgent Center, the AI layer of an eWallet platform.
Your only job is to call the extract_financial_intent function with structured data from the user's message.

Never respond with plain text. Always call the function.

Supported intents:
- balance_inquiry: user wants to know their balance or account info
- transaction_details_inquiry: user asks about a specific past transaction
- recurring_payment: user wants to set up, view, or cancel a scheduled/recurring payment (e.g. rent, subscriptions)
- expense_tracking: user wants to see, summarise, or export their spending history
- photo_claim: user sends a receipt or invoice image and wants to log or claim it
- unknown: message does not match any supported intent

Entity extraction rules:
- For recurring_payment: extract recipient, amount, currency, frequency, day_of_month if mentioned
- For expense_tracking: extract date_range, category, merchant if mentioned
- For photo_claim: note if the user explicitly asks to submit/save/claim (action field)
"""

EXTRACT_INTENT_TOOL = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="extract_financial_intent",
            description="Extract the user's financial intent and any relevant entities from their message.",
            parameters={
                "type": "object",
                "properties": {
                    "intent": {
                        "type": "string",
                        "enum": [
                            "balance_inquiry",
                            "transaction_details_inquiry",
                            "recurring_payment",
                            "expense_tracking",
                            "photo_claim",
                            "unknown",
                        ],
                    },
                    "confidence": {
                        "type": "number",
                        "description": "Confidence score between 0 and 1",
                    },
                    "entities": {
                        "type": "object",
                        "description": "Extracted values relevant to the intent",
                        "properties": {
                            "account_id":    {"type": "string"},
                            "transaction_id": {"type": "string"},
                            "recipient":     {"type": "string"},
                            "amount":        {"type": "number"},
                            "currency":      {"type": "string"},
                            "frequency":     {"type": "string"},   # "monthly" | "weekly"
                            "day_of_month":  {"type": "number"},
                            "date_range":    {"type": "string"},   # e.g. "last month"
                            "category":      {"type": "string"},   # e.g. "food"
                            "action":        {"type": "string"},   # "submit" | "save" | "claim"
                        },
                    },
                },
                "required": ["intent", "confidence"],
            },
        )
    ]
)
