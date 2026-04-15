"""WhatsApp platform adapter — bridges WhatsApp webhooks to the agent pipeline."""
import structlog
from typing import Any

from iagent.api.schemas.chat import ChatResponse
from iagent.api.schemas.ui_cards import BalanceCard, ErrorCard
from iagent.integrations.platforms.base import BasePlatformAdapter, InboundMessage
from iagent.integrations.platforms.whatsapp.client import WhatsAppClient
from iagent.integrations.platforms.whatsapp.models import WhatsAppMessage, WhatsAppWebhookPayload
from iagent.integrations.platforms.whatsapp.verifier import WhatsAppWebhookVerifier

log = structlog.get_logger(__name__)


class WhatsAppAdapter(BasePlatformAdapter):
    """Converts WhatsApp webhook payloads to InboundMessages and sends responses back."""

    def __init__(
        self,
        client: WhatsAppClient,
        verifier: WhatsAppWebhookVerifier,
    ) -> None:
        self._client = client
        self._verifier = verifier

    @property
    def platform_name(self) -> str:
        return "whatsapp"

    async def parse_webhook(self, payload: dict[str, Any]) -> list[InboundMessage]:
        """Extract actionable messages from a WhatsApp webhook payload."""
        try:
            event = WhatsAppWebhookPayload(**payload)
        except Exception as exc:
            log.warning("whatsapp_webhook_parse_failed", error=str(exc))
            return []

        messages: list[InboundMessage] = []

        for entry in event.entry:
            for change in entry.changes:
                if change.field != "messages":
                    continue
                for raw_msg in change.value.messages:
                    try:
                        msg = WhatsAppMessage.from_raw(raw_msg)

                        # Skip non-text/image types for now
                        if msg.type == "text" and msg.text:
                            text = msg.text.body
                            media_urls: list[str] = []
                        elif msg.type == "image" and msg.image:
                            text = msg.image.caption or "photo"
                            # TODO: call self._client.download_media(msg.image.id) and upload to blob storage
                            # TODO: set media_urls to the blob URL(s) for the orchestrator
                            media_urls = []
                        else:
                            # TODO: handle audio (speech-to-text), document (OCR for receipts)
                            continue

                        messages.append(InboundMessage(
                            platform=self.platform_name,
                            platform_user_id=msg.from_,
                            user_id=msg.from_,   # TODO: resolve WhatsApp number → internal user_id via IAccountClient
                            message=text,
                            message_id=msg.id,
                            media_urls=media_urls,
                            raw=raw_msg,
                        ))
                    except Exception as exc:
                        log.warning("whatsapp_message_parse_failed", error=str(exc))

        return messages

    async def send_response(
        self,
        inbound: InboundMessage,
        response: ChatResponse,
    ) -> None:
        """Format ChatResponse as a WhatsApp message and send it."""
        to = inbound.platform_user_id
        card = response.ui

        if isinstance(card, BalanceCard):
            text = self._format_balance_card(card)
            await self._client.send_text(to, text)

        elif isinstance(card, ErrorCard):
            await self._client.send_text(to, f"⚠️ {card.message}")

        else:
            # TODO: add formatters for RecurringPaymentCard, ExpenseCard, PhotoClaimCard
            await self._client.send_text(to, "Done ✓")

    async def verify_webhook(self, request_data: dict[str, Any]) -> bool:
        """Verify hub challenge or POST signature."""
        # TODO: plug in verifier.verify_signature for POST requests
        return True

    @staticmethod
    def _format_balance_card(card: BalanceCard) -> str:
        """Convert a BalanceCard to a WhatsApp-friendly text message."""
        lines = ["💰 *Your Balance*\n"]
        for acc in card.accounts:
            lines.append(
                f"• {acc.currency}  Available: {acc.available:,.2f}  "
                f"Pending: {acc.pending:,.2f}"
            )
        return "\n".join(lines)
