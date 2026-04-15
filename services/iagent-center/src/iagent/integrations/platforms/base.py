from abc import ABC, abstractmethod
from typing import Any

from iagent.api.schemas.chat import ChatResponse


class InboundMessage:
    """Normalised inbound message from any platform.

    Created by each platform adapter from the raw webhook payload.
    Passed into ContextBuilder so the rest of the pipeline stays platform-agnostic.
    """

    def __init__(
        self,
        platform: str,           # "whatsapp" | "mobile" | "telegram"
        platform_user_id: str,   # phone number, chat ID, etc.
        user_id: str,            # internal user ID (resolved by adapter)
        message: str,            # normalised text content
        message_id: str = "",    # platform message ID (for dedup / read receipts)
        media_urls: list[str] | None = None,  # pre-signed URLs for images / docs
        raw: dict[str, Any] | None = None,    # original webhook payload (for debugging)
    ) -> None:
        self.platform = platform
        self.platform_user_id = platform_user_id
        self.user_id = user_id
        self.message = message
        self.message_id = message_id
        self.media_urls = media_urls or []
        self.raw = raw or {}


class BasePlatformAdapter(ABC):
    """Contract every platform adapter must fulfil.

    Adapters sit at the edges of the system:
      Inbound:  raw webhook payload → InboundMessage (→ ContextBuilder → Orchestrator)
      Outbound: ChatResponse + InboundMessage → platform-specific send call
    """

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Identifier used in logs, metrics and AgentContext.platform."""
        ...

    @abstractmethod
    async def parse_webhook(self, payload: dict[str, Any]) -> list[InboundMessage]:
        """Parse a raw webhook payload into one or more normalised InboundMessages.

        One webhook may carry multiple messages (WhatsApp batches events).
        Returns [] if the payload carries no actionable messages (e.g. delivery receipts).

        # TODO: handle media messages (images → media_urls)
        # TODO: handle reaction / status update events (return [])
        """
        ...

    @abstractmethod
    async def send_response(
        self,
        inbound: InboundMessage,
        response: ChatResponse,
    ) -> None:
        """Format and deliver a ChatResponse back to the user on this platform.

        # TODO: convert ChatResponse.ui cards to platform-specific format
        # TODO: handle send failures with retry
        """
        ...

    @abstractmethod
    async def verify_webhook(self, request_data: dict[str, Any]) -> bool:
        """Return True if the incoming webhook can be verified as authentic.

        # TODO: implement platform-specific signature verification
        """
        ...
