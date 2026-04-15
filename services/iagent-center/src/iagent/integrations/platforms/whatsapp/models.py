"""Pydantic models that mirror the WhatsApp Cloud API webhook payload shape.

Reference: https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks/payload-examples
"""
from typing import Any
from pydantic import BaseModel


class WhatsAppTextBody(BaseModel):
    body: str


class WhatsAppImageBody(BaseModel):
    id: str           # media ID — must be downloaded via Graph API
    mime_type: str
    sha256: str = ""
    caption: str = ""


class WhatsAppMessage(BaseModel):
    id: str            # unique message ID
    from_: str         # sender phone number (field is "from" in JSON)
    timestamp: str
    type: str          # "text" | "image" | "audio" | "document" | "interactive"
    text: WhatsAppTextBody | None = None
    image: WhatsAppImageBody | None = None

    model_config = {"populate_by_name": True}

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> "WhatsAppMessage":
        """Parse a raw message dict, remapping 'from' → 'from_'."""
        data = dict(raw)
        data["from_"] = data.pop("from", "")
        return cls(**data)


class WhatsAppContact(BaseModel):
    wa_id: str
    profile: dict[str, Any] = {}


class WhatsAppMetadata(BaseModel):
    display_phone_number: str
    phone_number_id: str


class WhatsAppValue(BaseModel):
    messaging_product: str
    metadata: WhatsAppMetadata
    contacts: list[WhatsAppContact] = []
    messages: list[dict[str, Any]] = []   # parsed manually via WhatsAppMessage.from_raw
    statuses: list[dict[str, Any]] = []   # delivery / read receipts — ignored


class WhatsAppChange(BaseModel):
    value: WhatsAppValue
    field: str


class WhatsAppEntry(BaseModel):
    id: str
    changes: list[WhatsAppChange]


class WhatsAppWebhookPayload(BaseModel):
    """Root model for all incoming WhatsApp webhook events."""
    object: str
    entry: list[WhatsAppEntry]
