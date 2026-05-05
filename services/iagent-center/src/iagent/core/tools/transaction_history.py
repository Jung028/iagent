from typing import Any

from iagent.integrations.iaccount import IAccountClient
from iagent.integrations.ibusiness import IBusinessClient
from iagent.integrations.iuser import IUserClient
from difflib import get_close_matches

from typing import Any

from iagent.integrations.iaccount import IAccountClient
from iagent.integrations.ibusiness import IBusinessClient
from iagent.integrations.iuser import IUserClient
from difflib import get_close_matches

# Fields that BusinessTransactionHistoryRequest accepts — anything else is stripped
_ALLOWED_PARAMS = {
    "gmtCreate", "payerAccountId", "payerName",
    "txnType", "txnStatus", "amountMin", "amountMax",
    "category", "pageNo", "pageSize",
}

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

    # Only do contact lookup if payeeName was actually provided
    payee_name = params.get("payeeName")
    if payee_name and payee_name.strip():
        user_info = user_profile or await user_client.query_user_info(user_id, phone_no=phone_no, **ctx) or {}
        contact_cfg = user_info.get("contactConfig") or {}
        contacts = contact_cfg.get("userContactList") or []
        names = [c.get("displayName", "") for c in contacts if isinstance(c, dict)]

        if names:
            matches = get_close_matches(payee_name, names, n=1, cutoff=0.5)
            if matches:
                matched_name = matches[0]
                match = next((c for c in contacts if c["displayName"] == matched_name), None)
                if match:
                    payerAccount = await account_client.get_account_by_user_id(match["userId"], **ctx)
                    params["payerAccountId"] = payerAccount["accountId"]

    # Strip any LLM fields Java doesn't know about (e.g. payeeName, confidence)
    clean_params = {k: v for k, v in params.items() if k in _ALLOWED_PARAMS}

    #clean up gmtCreate to fit the ISO format 
    if "gmtCreate" in clean_params and clean_params["gmtCreate"]:
        gmt = str(clean_params["gmtCreate"]).strip().strip('"').strip("'")
        gmt = gmt.split("+")[0].strip()   # strip timezone offset
        gmt = gmt.replace(" ", "T")       # space → T
        if "T" not in gmt:
            gmt = f"{gmt}T00:00:00"
        gmt = gmt[:19]                    # truncate to "YYYY-MM-DDTHH:MM:SS" — drop microseconds
        clean_params["gmtCreate"] = gmt

    # Fetch account ID then query
    account = await account_client.get_account_by_user_id(user_id, **ctx)
    account_id = account["accountId"]

    transaction_history_result = await business_client.query_transaction_history(account_id, clean_params, **ctx)
    transactions = transaction_history_result or []

    return [
        {
            "txnId": t.get("txnId"),
            "gmtCreate": t.get("gmtCreate"),
            "amount": t.get("amount"),
            "payeeAccountId": t.get("payeeAccountId"),
            "transactionType": t.get("transactionType"),
            "completedAt": t.get("gmtCompleted"),
            "currency": t.get("currency"),
            "status": t.get("status"),
            "extInfo": t.get("extInfo"),
        }
        for t in transactions
    ]