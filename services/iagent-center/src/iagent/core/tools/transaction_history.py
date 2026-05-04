from typing import Any

from iagent.integrations.iaccount import IAccountClient
from iagent.integrations.ibusiness import IBusinessClient
from iagent.integrations.iuser import IUserClient
from difflib import get_close_matches

async def handle(
    user_id:str,
    phone_no: str,
    account_client: IAccountClient,
    business_client: IBusinessClient,
    user_client: IUserClient,
    params: dict,
    user_profile: dict | None = None,
    **ctx: Any,
) -> list[dict[str, Any]]:
    
    # we need to add a check here, to ensure that the user's request for the payeeName is someone within his contacts, 
    # check within the contact list, it should be able to handle even if half of the name is gone for example
    # send 20 to adam. or send 20 to ad
    user_info = user_profile or await user_client.query_user_info(user_id, phone_no=phone_no, **ctx) or {}

    contact_cfg = user_info.get("contactConfig") or {}
    contacts = contact_cfg.get("userContactList") or []

    payeeName = params.get("payeeName")

    names = [
        c.get("displayName", "")
        for c in contacts
        if isinstance(c, dict)
    ]
    # if names not present in contacts list, then return "no contacts list"
    if not names: 
        return None
     
    if names is not None and payeeName and payeeName.strip():
        # if the payeeName is not present in the first place, continue query transaction history with the other 
        # required parameters
        matches = get_close_matches(payeeName, names, n=1, cutoff=0.5)
        if matches:
            matched_name = matches[0]
            match = next(c for c in contacts if c["displayName"] == matched_name)

        if match:
            # get payerAccountId by userId 
            payerAccount = await account_client.get_account_by_user_id(match["userId"], **ctx)
            params["payerAccountId"] = payerAccount["accountId"]
    
    

    # fetch the list of transaction history from the ibusiness, by passing in the account Id, so we query iaccount first, 
    account = await account_client.get_account_by_user_id(user_id, **ctx)
    account_id = account["accountId"]

    transaction_history_result = await business_client.query_transaction_history(account_id, params, **ctx)
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
