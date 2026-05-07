from difflib import get_close_matches
from typing import Any

from iagent.integrations.iaccount import IAccountClient
from iagent.integrations.ibusiness import IBusinessClient
from iagent.integrations.iuser import IUserClient

DEFINITION: dict[str, Any] = {
    "name": "query_transactions",
    "description": (
        "Fetch the user's transaction history with optional filters. "
        "Use for: listing transactions, history, spending analysis, "
        "yes/no questions ('have I paid X?'), "
        "superlatives ('most expensive', 'latest', 'oldest'), "
        "and cross-period comparisons (call twice with different date ranges)."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "gmtCreateStart": {
                "type": "string",
                "description": "Start of datetime range YYYY-MM-DDTHH:MM:SS. Always pair with gmtCreateEnd.",
            },
            "gmtCreateEnd": {
                "type": "string",
                "description": "End of datetime range YYYY-MM-DDTHH:MM:SS. Always pair with gmtCreateStart.",
            },
            "payerName": {
                "type": "string",
                "description": "Filter by who paid INTO my account (incoming). e.g. 'received from Ali'.",
            },
            "payeeName": {
                "type": "string",
                "description": "Filter by who I paid (outgoing). e.g. 'sent to Ali', 'paid Ali'.",
            },
            "payerAccountId": {"type": "string"},
            "payeeAccountId": {"type": "string"},
            "txnType": {
                "type": "string",
                "enum": ["TRANSFER", "REFUND", "DEPOSIT", "TOP_UP"],
            },
            "txnStatus": {
                "type": "string",
                "enum": ["PENDING", "FINISH", "FAILED"],
            },
            "amountMin": {"type": "number", "description": "Minimum amount filter."},
            "amountMax": {"type": "number", "description": "Maximum amount filter."},
            "category": {
                "type": "string",
                "enum": [
                    "GROCERIES", "FOOD_DINING", "TRANSPORT", "FUEL", "SHOPPING",
                    "ENTERTAINMENT", "UTILITIES", "RENT", "HEALTHCARE", "EDUCATION",
                    "TRANSFER", "TOP_UP", "OTHER",
                ],
            },
            "sortField": {
                "type": "string",
                "enum": ["gmtCreate", "amount"],
                "description": "Field to sort by. Use 'amount' for most/least expensive. Default gmtCreate.",
            },
            "sortOrder": {
                "type": "string",
                "enum": ["ASC", "DESC"],
                "description": "ASC = oldest/cheapest first. DESC = newest/most expensive first. Default DESC.",
            },
            "pageNo":   {"type": "integer"},
            "pageSize": {"type": "integer", "description": "Use 1 for latest/oldest/most expensive queries."},
        },
    },
}

# Fields that BusinessTransactionHistoryRequest accepts — anything else is stripped
_ALLOWED_PARAMS = {
    "gmtCreateStart", "gmtCreateEnd",
    "payerAccountId", "payeeAccountId", "payerName",
    "txnType", "txnStatus", "amountMin", "amountMax",
    "category", "sortField", "sortOrder", "pageNo", "pageSize",
}


def _normalize_dt(value: str) -> str:
    """Normalize any datetime string to YYYY-MM-DDTHH:MM:SS."""
    v = str(value).strip().strip('"').strip("'")
    v = v.split("+")[0].strip()   # strip timezone offset e.g. +00:00
    v = v.replace(" ", "T")       # space separator → T
    if "T" not in v:
        v = f"{v}T00:00:00"
    return v[:19]                 # truncate microseconds


async def handle(
    user_id: str,
    phone_no: str,
    account_client: IAccountClient,
    business_client: IBusinessClient,
    user_client: IUserClient,
    params: dict,
    user_profile: dict | None = None,
    **ctx: Any,
) -> list[dict[str, Any]]:

    # Contact lookup — only when payeeName is provided (outgoing transfer filter)
    payee_name = params.get("payeeName")
    if payee_name and payee_name.strip():
        user_info = user_profile or await user_client.query_user_info(
            user_id, phone_no=phone_no, **ctx
        ) or {}
        contacts = (user_info.get("contactConfig") or {}).get("userContactList") or []
        names = [c.get("displayName", "") for c in contacts if isinstance(c, dict)]

        if names:
            matches = get_close_matches(payee_name, names, n=1, cutoff=0.5)
            if matches:
                match = next(
                    (c for c in contacts if c["displayName"] == matches[0]), None
                )
                if match:
                    payee_account = await account_client.get_account_by_user_id(
                        match["userId"], **ctx
                    )
                    params["payeeAccountId"] = payee_account["accountId"]

    # Strip fields Java doesn't know about (payeeName, confidence, intent, etc.)
    clean_params = {k: v for k, v in params.items() if k in _ALLOWED_PARAMS}

    # Normalize datetime fields to ISO-8601 without microseconds
    for field in ("gmtCreateStart", "gmtCreateEnd"):
        if clean_params.get(field):
            clean_params[field] = _normalize_dt(clean_params[field])

    # Resolve account then fetch
    account = await account_client.get_account_by_user_id(user_id, **ctx)
    account_id = account["accountId"]

    transactions = await business_client.query_transaction_history(
        account_id, clean_params, **ctx
    ) or []

    return [
        {
            "txnId":           t.get("txnId"),
            "gmtCreate":       t.get("gmtCreate"),
            "amount":          t.get("amount"),
            "payeeAccountId":  t.get("payeeAccountId"),
            "transactionType": t.get("transactionType"),
            "completedAt":     t.get("gmtCompleted"),
            "currency":        t.get("currency"),
            "status":          t.get("status"),
            "extInfo":         t.get("extInfo"),
        }
        for t in transactions
    ]
