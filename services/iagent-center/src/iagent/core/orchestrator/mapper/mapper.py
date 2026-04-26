

ENTITY_TO_API_MAP = {
    "payee_account_id": "payeeAccountId",
    "counterparty_name": "payeeName",
    "time_hint": "gmtCreate",
    "account_id": "accountId",
}

def map_entities_to_api_params(entities: dict):
    params = {}

    for k, v in entities.items():
        if v is None:
            continue

        api_key = ENTITY_TO_API_MAP.get(k, k)
        params[api_key] = v

    return params