from datetime import date

today = date.today().isoformat()

SYSTEM_PROMPT = f"""\
You are the intent classification engine for iAgent, an eWallet platform.
Your only job is to call extract_financial_intent with structured data from the user's message.
Never respond with plain text. Always call the function.

Today's date is {today}.

INTENT DEFINITIONS:
- balance_inquiry      : user wants to know their account balance
- transaction_search   : user wants to list or find transactions (show me, find, list)
- transaction_details  : user asks about ONE specific transaction by ID or description
- transaction_analyze  : user wants a summary or analysis of spending (how much, total, average, breakdown)
- transfer             : user wants to send money to someone
- top_up               : user wants to add money to their eWallet (top up, reload, add funds)
- unknown              : does not match any supported intent

DATE RULE — always resolve relative dates to a YYYY-MM-DD string using today's date ({today}):
- "last month"    → first day of last month        e.g. 2026-04-01
- "this month"    → first day of current month     e.g. 2026-05-01
- "last 3 months" → date 3 months ago              e.g. 2026-02-04
- "last week"     → date 7 days ago                e.g. 2026-04-27
- "this year"     → first day of current year      e.g. 2026-01-01
- If no date is mentioned, omit gmtCreate entirely.

TRANSFER RULE:
- payeeAccountNo is the recipient's exact account number (only if user states it explicitly)
- payeeName is the recipient's display name (used for fuzzy contact lookup)
- Extract whichever one the user mentions — not both unless both are stated.

TOP UP RULE:
- cardType defaults to DEBIT unless user explicitly says "credit card"
- isSaveCard is true ONLY if user explicitly says "save my card" or "remember my card"
- currency defaults to MYR unless user states otherwise
"""

EXTRACT_INTENT_TOOL = {
    "name": "extract_financial_intent",
    "description": "Extract the user's financial intent and structured entities. Only include fields explicitly mentioned by the user.",
    "input_schema": {
        "type": "object",
        "required": ["intent", "confidence"],
        "properties": {

            "intent": {
                "type": "string",
                "enum": [
                    "balance_inquiry",
                    "transaction_search",
                    "transaction_details",
                    "transaction_analyze",
                    "transfer",
                    "top_up",
                    "unknown",
                ],
            },

            "confidence": {
                "type": "number",
                "description": "Confidence score 0.0 to 1.0.",
            },

            "entities": {
                "type": "object",
                "description": "Structured values extracted from the message. Only include fields the user explicitly mentioned.",
                "properties": {

                    # ── transaction_search + transaction_analyze ──────────────
                    # Maps directly to BusinessTransactionHistoryRequest

                    "gmtCreate": {
                        "type": "string",
                        "description": (
                            "Date filter in YYYY-MM-DD format. "
                            "Resolve relative dates using today's date. "
                            "Examples: 'last month' → '2026-04-01', 'this month' → '2026-05-01'."
                        ),
                    },
                    "payerAccountId": {
                        "type": "string",
                        "description": "Filter transactions by a specific payer's account ID.",
                    },
                    "payerName": {
                        "type": "string",
                        "description": "Filter transactions by payer's display name.",
                    },
                    "pageNo": {
                        "type": "integer",
                        "description": "Page number for pagination. Starts at 1.",
                    },
                    "pageSize": {
                        "type": "integer",
                        "description": "Number of results per page. Default is 10.",
                    },

                    # ── transaction_details ───────────────────────────────────
                    # Maps directly to BusinessTransactionRecordRequest

                    "txnId": {
                        "type": "string",
                        "description": "Specific transaction ID. Required for transaction_details intent.",
                    },

                    # ── transfer ──────────────────────────────────────────────
                    # Maps directly to TransferRequest (transferInit step only)
                    # transferConfirm fields (password, transferToken) are never extracted by LLM

                    "payeeAccountNo": {
                        "type": "string",
                        "description": "Recipient's exact account number. Only extract if user explicitly states an account number.",
                    },
                    "payeeName": {
                        "type": "string",
                        "description": "Recipient's display name for contact lookup. Extract when user says a person's name.",
                    },
                    "transferType": {
                        "type": "string",
                        "enum": ["STANDARD", "QR"],
                        "description": "STANDARD for normal transfer, QR for QR code payment. Default STANDARD.",
                    },

                    # ── transfer + top_up (shared) ────────────────────────────

                    "amount": {
                        "type": "number",
                        "description": "Amount to transfer or top up.",
                    },
                    "currency": {
                        "type": "string",
                        "description": "Currency code e.g. MYR, USD. Default MYR if not stated.",
                    },

                    # ── top_up ────────────────────────────────────────────────
                    # Maps directly to TopUpRequest (createTopUpIntent step only)
                    # passwordPin is never extracted by LLM — entered by user in confirmation UI

                    "cardType": {
                        "type": "string",
                        "enum": ["DEBIT", "CREDIT"],
                        "description": "Card type for top up. Default DEBIT unless user explicitly says credit card.",
                    },
                    "isSaveCard": {
                        "type": "boolean",
                        "description": "True only if user explicitly says to save or remember their card.",
                    },
                },
            },
        },
    },
}