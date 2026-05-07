from typing import Any, Dict

from pydantic import BaseModel, Field, ConfigDict

from iagent.api.schemas.ui_cards import AnyUICard


class ChatRequest(BaseModel):
    """The JSON body the mobile app sends to POST /chat.

    In Java this would be: public record ChatRequest(String userId, String message) {}
    with Jackson deserializing the incoming JSON automatically.
    Pydantic does the same thing here.
    """
    model_config = ConfigDict(populate_by_name=True)

    user_id: str  # The authenticated user's ID, e.g. "user-abc-123"

    # The user's phone number, passed from the frontend session.
    phone_no: str | None = Field(default=None, alias="phoneNo")

    # The user's session ID, passed from the frontend session.
    session_id: str | None = Field(default=None, alias="sessionId")

    # Thread ID for RAG memory continuity across turns.
    thread_id: str | None = Field(default=None, alias="threadId")

    # Field() lets us add constraints and metadata to a field.
    # "min_length=1" means the message cannot be empty (raises a 422 error if violated).
    # "max_length=2000" prevents extremely large inputs from being sent to the LLM.
    # In Java Bean Validation this would be: @NotBlank @Size(min=1, max=2000) String message
    message: str = Field(min_length=1, max_length=2000)

    # Set to true when the user clicks the Confirm button on a ConfirmationCard.
    # This triggers transferInit and returns a PinInputCard.
    confirmed: bool = False

    # The user's PIN, submitted from a PinInputCard.
    # Triggers transferConfirm on the backend.
    pin: str | None = None


class ChatResponse(BaseModel):
    """The JSON body iAgent Center sends back to the mobile app.

    The mobile app reads:
    - "intent": to know what the AI understood
    - "ui": the card data to render on screen (its shape depends on the "type" field inside)
    - "requires_action": whether the user needs to do something (confirm, enter PIN, etc.)
    """

    # The classified intent as a string, e.g. "balance_inquiry" or "unknown".
    intent: str

    # "AnyUICard" is our union type from ui_cards.py — it is either a BalanceCard or ErrorCard.
    # Pydantic serialises whichever concrete type is stored here into JSON automatically,
    # including the "type" discriminator field so the mobile app knows which it is.
    ui: AnyUICard

    # " = False" sets a DEFAULT value of False.
    # This means if you create a ChatResponse without specifying requires_action,
    # it automatically becomes False. In Java: boolean requiresAction = false;
    requires_action: bool = False