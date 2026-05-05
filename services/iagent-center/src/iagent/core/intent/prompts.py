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

DATE RULE — always resolve to ISO-8601 datetime string "YYYY-MM-DDTHH:MM:SS" using today's date ({today}):
- "last month"      → first day of last month at midnight   e.g. 2026-04-01T00:00:00
- "this month"      → first day of current month            e.g. 2026-05-01T00:00:00
- "last 3 months"   → date 3 months ago at midnight         e.g. 2026-02-05T00:00:00
- "last week"       → date 7 days ago at midnight           e.g. 2026-04-28T00:00:00
- "this year"       → first day of current year             e.g. 2026-01-01T00:00:00
- "after 4pm today" → today at that time                    e.g. 2026-05-05T16:00:00
- "this morning"    → today at 06:00:00                     e.g. 2026-05-05T06:00:00
- "yesterday"       → yesterday at midnight                 e.g. 2026-05-04T00:00:00
- Date only, no time mentioned → default time to T00:00:00
- If no date is mentioned, omit gmtCreate entirely.

TRANSACTION FILTER RULES:
- txnType: only set if the user explicitly says a type ("show my top-ups" → TOP_UP, "transfers only" → TRANSFER, "refunds" → REFUND, "deposits" → DEPOSIT)
- txnStatus: "pending" → PENDING, "completed/done/successful" → FINISH, "failed" → FAILED
- amountMin/amountMax: extract numeric values when user says "more than 50", "under 200", "between 10 and 100"
- Do NOT guess or infer txnType/txnStatus if the user hasn't mentioned them.

CATEGORY RULE — map the user's natural language to the exact category code:
- "groceries / supermarket / wet market / pasar"        → GROCERIES
- "food / restaurant / cafe / mamak / dining / eat/makan" → FOOD_DINING
- "transport / grab / bus / lrt / toll / ride / taxi"   → TRANSPORT
- "fuel / petrol / gas / RON"                           → FUEL
- "shopping / retail / clothes / online / lazada"       → SHOPPING
- "entertainment / movie / cinema / games / streaming"  → ENTERTAINMENT
- "utilities / electricity / TNB / water / telco / bill"→ UTILITIES
- "rent / rental / landlord"                            → RENT
- "healthcare / clinic / doctor / pharmacy / hospital"  → HEALTHCARE
- "education / school / tuition / course / university"  → EDUCATION
- "transfer / sent to / paid person"                    → TRANSFER
- "top up / reload / add funds"                         → TOP_UP
- Only set category if the user explicitly mentions a spending type.

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
                            "Datetime filter in ISO-8601 format 'YYYY-MM-DDTHH:MM:SS'. "
                            "Always include the T and time part — default to T00:00:00 if user only mentions a date. "
                            "Examples: 'last month' → '2026-04-01T00:00:00', 'after 4pm today' → '2026-05-05T16:00:00'."
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
                    "txnType": {
                        "type": "string",
                        "enum": ["TRANSFER", "REFUND", "DEPOSIT", "TOP_UP"],
                        "description": (
                            "Filter by transaction type. "
                            "Use when user says 'show my top-ups', 'only transfers', 'refunds', etc."
                        ),
                    },
                    "txnStatus": {
                        "type": "string",
                        "enum": ["PENDING", "FINISH", "FAILED"],
                        "description": (
                            "Filter by transaction status. "
                            "FINISH = completed. Use when user says 'pending', 'failed', 'completed'."
                        ),
                    },
                    "amountMin": {
                        "type": "number",
                        "description": "Minimum transaction amount. Use when user says 'more than X' or 'above X'.",
                    },
                    "amountMax": {
                        "type": "number",
                        "description": "Maximum transaction amount. Use when user says 'less than X' or 'under X'.",
                    },
                    "category": {
                        "type": "string",
                        "enum": [
                            "GROCERIES",
                            "FOOD_DINING",
                            "TRANSPORT",
                            "FUEL",
                            "SHOPPING",
                            "ENTERTAINMENT",
                            "UTILITIES",
                            "RENT",
                            "HEALTHCARE",
                            "EDUCATION",
                            "TRANSFER",
                            "TOP_UP",
                            "OTHER",
                        ],
                        "description": (
                            "Transaction spending category. "
                            "Map the user's natural language to the closest category code. "
                            "Only set if the user explicitly mentions a spending type."
                        ),
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