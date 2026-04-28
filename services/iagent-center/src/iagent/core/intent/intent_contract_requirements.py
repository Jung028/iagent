from typing import Dict, List, TypedDict




class IntentFieldsContract(TypedDict): 
    required_fields: List[str]
    optional_fields: List[str]

class IntentContract(TypedDict): 
    transaction_select: IntentFieldsContract
    transaction_details: IntentFieldsContract
    transaction_analyze: IntentFieldsContract
    balance_inquiry: IntentFieldsContract

INTENT_REQUIREMENTS: Dict[str, IntentContract] = {
    "transaction_search": {
        "required": [],
        "optional": [
            "time_range",
            "counterparty_name",
            "counterparty_account_id",
            "amount_min",
            "amount_max",
            "currency",
            "status",
            "txn_type",
            "keyword",
            "sort_by",
            "sort_order",
            "limit",
            "offset",
        ],
    }, 
    "transaction_details": {
        "required" : ["transaction_id"],
        "optional" : [
            "account_id",
            "counterparty_name",
            "counterparty_account_id",
            "time_hint",
        ],
    },
    "transaction_analyze": {
        "required": ["time_range"],
        "optional": [
            "group_by",
            "txn_type",
            "status",
        ],
    },
    "balance_inquiry": {
        "required": [],
        "optional": [
            "spending"
        ]
    }
}