from typing import Any

from iagent.integrations.iaccount import IAccountClient
from iagent.integrations.ibusiness import IBusinessClient
from iagent.integrations.iuser import IUserClient

# DEFINITION is the Anthropic "tool schema" for this tool.
# It describes to Claude what this tool does and what arguments it needs.
# This same JSON schema is what we pass as part of the "tools" list when calling
# the Anthropic API in future agentic flows where the LLM decides which tool to call.
#
# "dict[str, Any]" is the type hint — a dictionary with string keys and any-type values.
# In Java: Map<String, Object>
DEFINITION: dict[str, Any] = {
    "name": "get_account_balance",
    "description": "Retrieve the account balance for a user.",
    "input_schema": {
        "type": "object",
        "properties": {
            "user_id": {"type": "string"},
        },
        "required": ["user_id"],
    },
}


async def handle(
    user_id: str,
    account_client: IAccountClient,
    business_client: IBusinessClient,
    user_client: IUserClient,
    **ctx: str,      # "**ctx" captures any extra keyword arguments as a dict.
                     # The caller passes request_id=, user_id_ctx= etc.
                     # We then forward them to the HTTP clients as context headers.
                     # In Java there's no direct equivalent — you'd pass a Map<String, String>.
) -> list[dict[str, Any]]:
    """Fetch account and balance data from the Java backend services.

    This function is the bridge between the AI layer and the financial data.
    It calls two Java services in sequence:
      1. iAccount  — to get the user's single account (1:1 relationship with userId)
      2. iBusiness — to get the live balance for that account

    Returns a single-element list, e.g.:
    [{"account_id": "acc-1", "currency": "USD", "available": 250.0, "pending": 0.0}]
    """

    # Step 1: Fetch the user's account from account center.
    # There is exactly one account per userId — no loop needed.
    # "**ctx" unpacks the ctx dict as keyword arguments:
    # If ctx = {"request_id": "abc"}, this is equivalent to:
    # account_client.get_account_by_user_id(user_id, request_id="abc")
    account = await account_client.get_account_by_user_id(user_id, **ctx)

    # Step 2: Fetch the live balance from the business service using the accountId.
    # Balance is always queried through iBusiness (BusinessBasicController.queryBalance),
    # never from account center.
    balance = await business_client.query_balance(account["accountId"], **ctx)

    # Return a single-element list to keep the response shape consistent.
    # .get("pending", 0.0) returns 0.0 if "pending" is absent — older records may omit it.
    return [
        {
            "account_id": account["accountId"],
            "currency": balance["currency"],
            "balance": balance["balance"],
            "pending": balance.get("pending", 0.0),
        }
    ]
