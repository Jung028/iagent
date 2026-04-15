"""WhatsApp Cloud API client — sends messages back to users.

Reference: https://developers.facebook.com/docs/whatsapp/cloud-api/messages
"""
import httpx
import structlog

log = structlog.get_logger(__name__)

GRAPH_API_BASE = "https://graph.facebook.com/v20.0"


class WhatsAppClient:
    """Sends messages via the WhatsApp Cloud API (Meta Graph API).

    One instance per app, stored on app.state.whatsapp_client.
    Uses httpx.AsyncClient for non-blocking HTTP calls.
    """

    def __init__(self, phone_number_id: str, access_token: str) -> None:
        self._phone_number_id = phone_number_id
        self._url = f"{GRAPH_API_BASE}/{phone_number_id}/messages"
        self._headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        self._http = httpx.AsyncClient(timeout=10.0)

    async def send_text(self, to: str, text: str) -> None:
        """Send a plain text message to a WhatsApp phone number.

        # TODO: handle 429 rate limit with backoff
        # TODO: emit whatsapp_message_sent metric
        """
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {"preview_url": False, "body": text},
        }
        response = await self._http.post(self._url, headers=self._headers, json=payload)
        if not response.is_success:
            log.error("whatsapp_send_failed", to=to, status=response.status_code, body=response.text)
            response.raise_for_status()

    async def send_interactive_buttons(
        self,
        to: str,
        body: str,
        buttons: list[dict],
    ) -> None:
        """Send an interactive message with quick-reply buttons.

        buttons format: [{"id": "confirm_pay", "title": "Confirm"}]

        # TODO: validate max 3 buttons (WhatsApp Cloud API limit)
        # TODO: add header and footer support
        """
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": body},
                "action": {
                    "buttons": [
                        {"type": "reply", "reply": {"id": b["id"], "title": b["title"]}}
                        for b in buttons
                    ]
                },
            },
        }
        response = await self._http.post(self._url, headers=self._headers, json=payload)
        response.raise_for_status()

    async def download_media(self, media_id: str) -> bytes:
        """Download a media file (image, document) by its WhatsApp media ID.

        # TODO: cache downloaded media temporarily to avoid re-fetching on retries
        # TODO: upload to blob storage and return a URL instead of raw bytes
        """
        url_response = await self._http.get(
            f"{GRAPH_API_BASE}/{media_id}",
            headers=self._headers,
        )
        url_response.raise_for_status()
        media_url = url_response.json()["url"]
        media_response = await self._http.get(media_url, headers=self._headers)
        media_response.raise_for_status()
        return media_response.content

    async def aclose(self) -> None:
        await self._http.aclose()
