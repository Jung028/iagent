from typing import Dict, List, TypedDict


class IntentFieldsContract(TypedDict):
    required: List[str]
    optional: List[str]


INTENT_REQUIREMENTS: Dict[str, IntentFieldsContract] = {

    "read": {
        "required": [],   # ReadAgent decides what to fetch — nothing required upfront
        "optional": [],
    },

    "transfer": {
        # Both required. payeeAccountNo can substitute for payeeName — see IntentValidator.
        "required": ["amount", "payeeName"],
        "optional": ["payeeAccountNo", "currency", "transferType"],
    },

    "top_up": {
        "required": ["amount"],
        "optional": ["currency", "cardType", "isSaveCard"],
    },
}
