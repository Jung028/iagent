from iagent.core.response_builder.card_factory import make_balance_card, make_error_card
from iagent.api.schemas.ui_cards import BalanceCard, ErrorCard


def test_balance_card_shape():
    card = make_balance_card([
        {"account_id": "acc-1", "currency": "USD", "available": 100.0, "pending": 5.0}
    ])
    assert isinstance(card, BalanceCard)
    assert card.type == "balance_card"
    assert card.accounts[0].available == 100.0
    assert card.accounts[0].currency == "USD"


def test_error_card_recoverable():
    card = make_error_card("unsupported_intent", "I can only help with balance inquiries.")
    assert isinstance(card, ErrorCard)
    assert card.recoverable is True
