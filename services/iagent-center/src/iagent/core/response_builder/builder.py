from typing import Any

from iagent.api.schemas.chat import ChatResponse
from iagent.core.response_builder.card_factory import make_balance_card, make_error_card, make_transaction_analysis_card, make_transaction_details_card, make_transaction_history_card, make_transaction_search_card
from iagent.core.models.intent import Intent


def build_balance_response(accounts_data: list[dict[str, Any]]) -> ChatResponse:
    """Wrap a BalanceCard in the full ChatResponse envelope.

    WHY two layers (card_factory + builder)?
    - card_factory knows HOW to build each specific card type (the shape of the data)
    - builder knows HOW to wrap any card in a ChatResponse (the envelope structure)
    Keeping them separate makes each easier to test and extend independently.

    In Java this is like having a CardFactory and a ResponseAssembler as separate services.
    """

    # Call make_balance_card() from card_factory.py to build the typed BalanceCard,
    # then wrap it in a ChatResponse.
    return ChatResponse(
        # "Intent.BALANCE_INQUIRY" is the enum member. When Pydantic serialises this
        # to JSON, it becomes the string "balance_inquiry" (because we use StrEnum).
        intent=Intent.BALANCE_INQUIRY,

        # "ui" holds the BalanceCard. ChatResponse.ui is typed as AnyUICard (a Union),
        # but Pydantic is fine storing a BalanceCard there — it matches the Union.
        ui=make_balance_card(accounts_data),

        # False = no further action needed from the user for a balance inquiry.
        requires_action=False,
    )

def build_transaction_details_response(transaction_details: dict[str, Any]) -> ChatResponse: 
    return ChatResponse(
        intent=Intent.TRANSACTION_DETAILS,
        ui=make_transaction_details_card(transaction_details),
        requires_action=False,
    )


def build_error_response(intent: str, code: str, message: str) -> ChatResponse:
    """Wrap an ErrorCard in the full ChatResponse envelope.

    Note that "intent" here is a plain str (not an Intent enum) because we might
    call this with Intent.UNKNOWN.value or any future unknown string.
    """
    return ChatResponse(
        intent=intent,
        ui=make_error_card(code=code, message=message, recoverable=True),
        requires_action=False,
    )


def build_transaction_analysis_response(result: list[dict[str, Any]]) -> ChatResponse:
    return ChatResponse(
        intent=Intent.TRANSACTION_ANALYZE,
        ui=make_transaction_analysis_card(result),
        requires_action=False,
    )

def build_transaction_search_response(result: list[dict[str, Any]]) -> ChatResponse: 
    return ChatResponse(
        intent=Intent.TRANSACTION_SEARCH,
        ui=make_transaction_search_card(result),
        requires_action=False,
    )

def build_transaction_history_response(transaction_history: list[dict[str, Any]]) -> ChatResponse:
    return ChatResponse(
        intent=Intent.TRANSACTION_ANALYZE,
        ui=make_transaction_history_card(transaction_history),
        requires_action=False,
    )

