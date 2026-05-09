from typing import Any

from iagent.integrations.iaccount import IAccountClient
from iagent.integrations.ibusiness import IBusinessClient
from iagent.integrations.iuser import IUserClient

DEFINITION: dict[str, Any] = {
    "name": "get_transaction_detail",
    "description": (
        "Get full details of ONE specific transaction by its ID. "
        "Use when the user provides a transaction ID (UUID), or when they want "
        "more detail on a specific transaction found via query_transactions."
    ),
    "input_schema": {
        "type": "object",
        "required": ["txn_id"],
        "properties": {
            "txn_id": {
                "type": "string",
                "description": "The transaction ID (UUID format)",
            },
        },
    },
}


async def handle(
        user_id: str,
        transaction_id: str,
        account_client: IAccountClient,
        business_client: IBusinessClient,
        user_client: IUserClient,
        **ctx: str,
) -> dict[str, Any]:
    """Fetch transaction details for a given user and transaction ID.

    Returns a normalised dict ready for card_factory / response_builder.
    """
    account = await account_client.get_account_by_user_id(user_id, **ctx)
    account_id = account["accountId"]

    # ibusiness already normalises the result — use it directly
    txn = await business_client.query_transaction_details(account_id, transaction_id, **ctx)

    return {
        "account_id":     account_id,
        "transaction_id": txn.get("transaction_id"),
        "payer_account_id": txn.get("payer_account_id"),
        "payee_account_id": txn.get("payee_account_id"),
        "amount":         txn.get("amount", 0.0),
        "currency":       txn.get("currency", "MYR"),
        "txn_type":       txn.get("txn_type"),
        "txn_status":     txn.get("txn_status"),
        "failure_reason": txn.get("failure_reason"),
        "created_at":     txn.get("created_at"),
        "completed_at":   txn.get("completed_at"),
    }
