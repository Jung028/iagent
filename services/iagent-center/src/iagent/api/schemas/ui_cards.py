# "datetime" is Python's built-in date/time type — similar to java.time.LocalDateTime.
from datetime import datetime

# "Annotated", "Literal", "Union" are from Python's "typing" module.
# They are used only for type hints — they have no effect at runtime.
# "Annotated" lets you attach extra metadata to a type.
# "Literal" means "this field can ONLY be this exact string value".
# "Union" means "this can be one of several types" — like an interface with multiple implementations.
from typing import Annotated, Literal, Union

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
    account_id: str
    txn_id: str
    amount: float
    currency: str
    payee: str | None = None
    txn_type: str | None = None
    created_at: str | None = None
    completed_at: str | None = None

class TransactionDetailsCard(BaseModel):
    type: Literal["transaction_details_card"] = "transaction_details_card"
    transaction_details: TransactionDetails


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
    Union[BalanceCard, ErrorCard, TransactionDetailsCard],
    Field(discriminator="type"),
]
