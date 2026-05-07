from datetime import date

today = date.today().isoformat()

SYSTEM_PROMPT = f"""\
You are the intent router for iAgent, an eWallet assistant.
Your only job is to call extract_intent with structured data from the user's message.
Never respond in plain text. Always call the function.

Today's date is {today}.

INTENT DEFINITIONS:
- read     : anything that asks a question, requests information, or is conversational
             (balance, transaction history, spending analysis, greetings, "what can you do", unknown)
- transfer : user wants to send money to someone
- top_up   : user wants to add money to their eWallet (top up, reload, add funds)

When in doubt between read and write, always choose read.
Greetings, questions, and anything not clearly money-movement → read.

ENTITY EXTRACTION (only for transfer and top_up):

transfer entities:
  amount        : numeric amount to send (required for transfer)
  payeeName     : recipient's display name, for contact lookup
  payeeAccountNo: recipient's exact account number (only if user states it)
  currency      : currency code, default MYR
  transferType  : STANDARD or QR, default STANDARD

top_up entities:
  amount    : numeric amount to top up (required)
  currency  : currency code, default MYR
  cardType  : DEBIT or CREDIT — default DEBIT unless user says "credit card"
  isSaveCard: true ONLY if user explicitly says "save my card" or "remember my card"

For read intent, do not extract any entities — the assistant handles querying itself.
"""

EXTRACT_INTENT_TOOL = {
    "name": "extract_intent",
    "description": "Classify the user's message as read, transfer, or top_up and extract structured entities.",
    "input_schema": {
        "type": "object",
        "required": ["intent", "confidence"],
        "properties": {

            "intent": {
                "type": "string",
                "enum": ["read", "transfer", "top_up"],
            },

            "confidence": {
                "type": "number",
                "description": "Confidence score 0.0 to 1.0.",
            },

            "entities": {
                "type": "object",
                "description": "Structured values for transfer or top_up only. Leave empty for read.",
                "properties": {

                    # ── transfer ──────────────────────────────────────────────
                    "amount": {
                        "type": "number",
                        "description": "Amount to transfer or top up.",
                    },
                    "payeeName": {
                        "type": "string",
                        "description": "Recipient display name for contact lookup.",
                    },
                    "payeeAccountNo": {
                        "type": "string",
                        "description": "Recipient's exact account number.",
                    },
                    "currency": {
                        "type": "string",
                        "description": "Currency code e.g. MYR. Default MYR.",
                    },
                    "transferType": {
                        "type": "string",
                        "enum": ["STANDARD", "QR"],
                        "description": "Default STANDARD.",
                    },

                    # ── top_up ────────────────────────────────────────────────
                    "cardType": {
                        "type": "string",
                        "enum": ["DEBIT", "CREDIT"],
                        "description": "Default DEBIT.",
                    },
                    "isSaveCard": {
                        "type": "boolean",
                        "description": "True only if user explicitly asks to save their card.",
                    },
                },
            },
        },
    },
}
