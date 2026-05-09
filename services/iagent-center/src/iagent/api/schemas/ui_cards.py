# "datetime" is Python's built-in date/time type — similar to java.time.LocalDateTime.
from datetime import datetime

# "Annotated", "Literal", "Union" are from Python's "typing" module.
# They are used only for type hints — they have no effect at runtime.
# "Annotated" lets you attach extra metadata to a type.
# "Literal" means "this field can ONLY be this exact string value".
# "Union" means "this can be one of several types" — like an interface with multiple implementations.
from typing import Annotated, List, Literal, Union

# Pydantic is a data validation library — similar to Java's Bean Validation (javax.validation)
# combined with Jackson for JSON serialization/deserialization.
# BaseModel is the base class for all Pydantic models (like Java DTOs/Records).
# Field lets you add extra configuration to a field (like @JsonProperty in Jackson).
from pydantic import BaseModel, Field


# "class AccountBalance(BaseModel)" is a Pydantic model — a data class with
# automatic JSON parsing, validation, and serialization built in.
# In Java this would be a DTO record: public record AccountBalance(String accountId, ...) {}
class AccountBalance(BaseModel):
    account_id: str    # Java: String accountId
    currency: str      # e.g. "USD", "MYR"
    balance: float   # float in Python is a 64-bit double — same as Java's double
    pending: float     # money that is reserved but not yet settled


class TransactionDetails(BaseModel):
    account_id: str | None = None
    txn_id: str
    amount: float
    currency: str
    txn_type: str | None = None
    created_at: str | None = None
    completed_at: str | None = None

class TransactionDetailsCard(BaseModel):
    type: Literal["transaction_details_card"] = "transaction_details_card"
    transaction_details: TransactionDetails

class TransactionHistoryCard(BaseModel):
    type: Literal["transaction_history_card"] = "transaction_history_card"
    transaction_history: List[TransactionDetails]

class AnalysisSummary(BaseModel):
    count: int | None = None
    average: float | None = None
    total: float | None = None
    currency: str = "MYR"
    survival_forecast: str | None = None
    summary: str


class TransactionAnalysisCard(BaseModel):
    type: Literal["transaction_analysis_card"] = "transaction_analysis_card"
    analysis: AnalysisSummary

class BalanceCard(BaseModel):
    # "Literal["balance_card"]" means this field MUST always equal the string "balance_card".
    # It can never be anything else. The " = "balance_card" " sets the default value
    # so it's automatically filled in — you never need to pass it manually.
    #
    # WHY: The mobile frontend reads the "type" field to know which UI component to render.
    # This is the "discriminator" pattern — like a Java sealed class or a Jackson @JsonTypeInfo.
    type: Literal["balance_card"] = "balance_card"

    # "list[AccountBalance]" is a typed list — like Java's List<AccountBalance>.
    # Python uses lowercase "list" (not "List") for built-in types since Python 3.9+.
    accounts: list[AccountBalance]

    # The timestamp when this balance data was fetched from the backend.
    as_of: datetime


class TextResponseCard(BaseModel):
    """Natural language answer from the ReadAgent.
    Used when the response is a conversational answer rather than a structured data card
    e.g. "Yes, you sent RM 50.00 to Ali on 3 May 2026."
    """
    type: Literal["text_response"] = "text_response"
    message: str

class ResponseItem(BaseModel):
    """One line in a section — either a key/value pair OR a plain bullet."""
    label: str | None = None   # e.g. "Total amount"  — None for plain bullets
    value: str | None = None   # e.g. "RM 1,011.00"   — None for plain bullets
    text:  str | None = None   # plain bullet text     — None for key/value rows


class ResponseSection(BaseModel):
    title: str | None = None
    items: list[ResponseItem] = []


class StructuredResponseCard(BaseModel):
    """Rich structured response from the ReadAgent.
    Used when the answer has multiple sections, bullet points, or key-value data.
    """
    type:     Literal["structured_response"] = "structured_response"
    summary:  str                              # one-line answer at the top
    sections: list[ResponseSection] = []       # optional breakdown sections


class ConfirmationCard(BaseModel):
    """Shown to the user before a write operation is executed."""
    type:    Literal["confirmation_card"] = "confirmation_card"
    message: str   # e.g. "Confirm transfer of RM 50.00 to Ali?"
    action:  str   # action_type string, e.g. "write_transfer"


class PinInputCard(BaseModel):
    """Shown after the user confirms — frontend calls transferConfirm directly with these fields."""
    type:           Literal["pin_input_card"] = "pin_input_card"
    message:        str   # e.g. "Enter your 6-digit PIN to authorise the transfer"
    action:         str   # e.g. "write_transfer"
    transfer_token: str = ""   # opaque token from transferInit — passed straight to transferConfirm
    account_id:     str = ""   # payer accountId — passed straight to transferConfirm


class BookkeepingEntry(BaseModel):
    vendor:      str | None = None
    date:        str | None = None   # YYYY-MM-DD
    amount:      float | None = None
    currency:    str | None = None
    category:    str | None = None
    description: str | None = None


class BookkeepingCard(BaseModel):
    type:                  Literal["bookkeeping_card"] = "bookkeeping_card"
    entry:                 BookkeepingEntry
    missing_fields:        List[str] = []
    clarifying_questions:  List[str] = []
    message:               str


class ErrorCard(BaseModel):
    # Same discriminator pattern as BalanceCard — mobile reads "type" = "error_card"
    # and knows to show an error UI instead of a balance UI.
    type: Literal["error_card"] = "error_card"

    # A short machine-readable error code (e.g. "unsupported_intent", "service_unavailable").
    # The mobile app can switch on this to show different error messages.
    code: str

    # A human-readable message shown to the user.
    message: str

    # If True, the user can try again (e.g. "service is busy, retry").
    # If False, they cannot recover without outside help (e.g. "account locked").
    recoverable: bool


# "AnyUICard" is a TYPE ALIAS — it gives a name to a complex type so we can
# reuse it without repeating the full definition everywhere.
#
# "Union[BalanceCard, ErrorCard]" means "this value is either a BalanceCard OR an ErrorCard".
# In Java this would be: interface UICard {} with BalanceCard and ErrorCard implementing it.
#
# "Annotated[..., Field(discriminator="type")]" tells Pydantic to look at the "type" field
# to decide WHICH model to deserialise into. When the JSON has "type": "balance_card",
# Pydantic instantiates a BalanceCard. When it sees "type": "error_card", it makes an ErrorCard.
# In Java Jackson this is: @JsonTypeInfo(use=Id.NAME, property="type")
AnyUICard = Annotated[
    Union[
        BalanceCard,
        ConfirmationCard,
        PinInputCard,
        BookkeepingCard,
        ErrorCard,
        TextResponseCard,
        StructuredResponseCard,
        TransactionDetailsCard,
        TransactionHistoryCard,
        TransactionAnalysisCard,
    ],
    Field(discriminator="type"),
]
