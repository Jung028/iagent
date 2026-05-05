from typing import Dict, List, TypedDict


class IntentFieldsContract(TypedDict):
    required: List[str]
    optional: List[str]


INTENT_REQUIREMENTS: Dict[str, IntentFieldsContract] = {

    "balance_inquiry": {
        "required": [],
        "optional": [],          # accountId comes from session, nothing for user to provide
    },

    "transaction_search": {
        "required": [],          # no required fields — bare "show my transactions" is valid
        "optional": [
            "gmtCreate",         # date filter (start date)
            "payerName",         # filter by payer name
            "payerAccountId",    # filter by payer account
            "txnType",           # TRANSFER | REFUND | DEPOSIT | TOP_UP
            "txnStatus",         # PENDING | FINISH | FAILED
            "amountMin",         # minimum amount filter
            "amountMax",         # maximum amount filter
            "category",          # GROCERIES | FOOD_DINING | TRANSPORT | FUEL | SHOPPING |
                                 # ENTERTAINMENT | UTILITIES | RENT | HEALTHCARE | EDUCATION |
                                 # TRANSFER | TOP_UP | OTHER
            "pageNo",            # pagination
            "pageSize",          # pagination
        ],
    },

    "transaction_details": {
        "required": ["txnId"],   # must have a transaction ID to look up
        "optional": [],
    },

    "transaction_analyze": {
        "required": ["gmtCreate"],  # must have a date range to analyze
        "optional": [
            "payerName",            # narrow analysis to a specific person
            "payerAccountId",
            "txnType",              # analyse only a specific type e.g. TOP_UP
            "txnStatus",            # analyse only completed / pending / failed
            "amountMin",            # narrow to a spend bracket
            "amountMax",
            "category",             # analyse by spending category e.g. GROCERIES
        ],
    },

    "transfer": {
        "required": ["amount"],                        # must know how much
        "optional": [
            "payeeName",                               # resolved via contact lookup
            "payeeAccountNo",                          # if user states account number directly
            "currency",                                # defaults to MYR
            "transferType",                            # defaults to STANDARD
        ],
    },

    "top_up": {
        "required": ["amount"],   # must know how much
        "optional": [
            "currency",           # defaults to MYR
            "cardType",           # defaults to DEBIT
            "isSaveCard",         # defaults to False
        ],
    },
}