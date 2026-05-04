from datetime import datetime, timezone
from typing import Any

from iagent.api.schemas.ui_cards import AccountBalance, AnalysisSummary, BalanceCard, ErrorCard, TransactionAnalysisCard, TransactionDetails, TransactionDetailsCard, TransactionHistoryCard


def make_balance_card(accounts_data: list[dict[str, Any]]) -> BalanceCard:
    """Convert raw account dicts (from tools/balance.py) into a BalanceCard Pydantic model.

    This function is a "factory" — it creates and returns a typed object.
    Keeping it separate from the route handler means card creation logic is easy to test
    in isolation (no HTTP, no LLM, no Redis needed in the test).

    In Java this would be a static factory method:
    public static BalanceCard from(List<Map<String, Object>> accountsData) { ... }
    """

    # LIST COMPREHENSION — this is one of Python's most distinctive features.
    # It's a compact way to build a new list by transforming each item in another list.
    #
    # In Java (verbose):
    #   List<AccountBalance> accounts = new ArrayList<>();
    #   for (Map<String, Object> a : accounts_data) {
    #       accounts.add(new AccountBalance(a.get("account_id"), ...));
    #   }
    #
    # In Python (compact):
    #   accounts = [AccountBalance(...) for a in accounts_data]
    #
    # Read it as: "for each 'a' in accounts_data, create an AccountBalance from it"
    accounts = [
        AccountBalance(
            account_id=a["account_id"],  # a["key"] reads a dict value — like Java's Map.get("key")
            currency=a["currency"],
            balance=a["balance"],
            pending=a.get("pending", 0.0),  # .get(key, default) — safe read with fallback
        )
        for a in accounts_data  # ← the loop part of the comprehension
    ]

    # Create and return a BalanceCard Pydantic model.
    # "datetime.now(tz=timezone.utc)" gets the current UTC timestamp.
    # In Java: ZonedDateTime.now(ZoneOffset.UTC)
    # The "as_of" field tells the mobile app WHEN the balance was fetched.
    return BalanceCard(accounts=accounts, as_of=datetime.now(tz=timezone.utc))

def make_transaction_details_card(transaction_data: dict[str, Any]) -> TransactionDetailsCard:
    return TransactionDetailsCard(
        transaction_details=TransactionDetails(
            account_id=transaction_data["account_id"],
            txn_id=transaction_data["transaction_id"],   # key from tools/transaction.py
            payee=transaction_data["payee_account_id"],
            amount=transaction_data["amount"],
            currency=transaction_data["currency"],
            txn_type=transaction_data["txn_type"],
            created_at=transaction_data["created_at"],
            completed_at=transaction_data["completed_at"],
        ) 
    )

def make_transaction_history_card(transaction_history: list[dict[str, Any]]) -> TransactionHistoryCard:

    return TransactionHistoryCard(
        transaction_history=[
            TransactionDetails(
                account_id=t.get("payeeAccountId"),
                txn_id=t.get("txnId"),
                txn_type=t.get("transactionType"),
                created_at=t.get("gmtCreate"),
                completed_at=t.get("completedAt"),
                amount=t.get("amount", 0.0),
                currency=t.get("currency", "MYR"),
            )
            # txn_id: str
            # amount: float
            # currency: str
            # payee: str | None = None
            # txn_type: str | None = None
            # created_at: str | None = None
            # completed_at: str | None = None
            for t in transaction_history
        ]
    )
    

def make_transaction_analysis_card(transaction_history: list[dict[str, Any]]) -> TransactionAnalysisCard:
        # Extract amounts — skip any transactions where amount is missing
    amounts = [t["amount"] for t in transaction_history if t.get("amount") is not None]

    count = len(amounts)
    total = sum(amounts)
    average = total / count if count > 0 else 0.0

    # Grab currency from the first transaction, fall back to MYR
    currency = transaction_history[0].get("currency", "MYR") if transaction_history else "MYR"

    # Plain summary for now — Claude will replace this string later
    summary = (
        f"You made {count} transaction(s) totalling {currency} {total:.2f}. "
        f"Your average transaction was {currency} {average:.2f}."
    )

    return TransactionAnalysisCard(
        type="transaction_analysis_card",
        analysis=AnalysisSummary(
            count=count,
            total=round(total, 2),
            average=round(average, 2),
            currency=currency,
            summary=summary,
        )
    )
    


def make_error_card(code: str, message: str, recoverable: bool = True) -> ErrorCard:
    """Create an ErrorCard to display when something goes wrong.

    "recoverable: bool = True" is a parameter with a default value.
    If the caller doesn't pass recoverable, it defaults to True.
    In Java: public static ErrorCard of(String code, String message, boolean recoverable)
    — but Java doesn't have default parameter values, so you'd need overloading.
    """
    return ErrorCard(code=code, message=message, recoverable=recoverable)
