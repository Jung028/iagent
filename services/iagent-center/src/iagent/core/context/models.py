from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentContext:
    # --- Identity ---
    user_id: str
    request_id: str
    session_id: str

    # --- LLM output ---
    raw_message: str
    intent: str
    confidence: float          # NOTE: float, not str
    entities: dict[str, Any] = field(default_factory=dict)

    # --- Conversation history ---
    history: list[dict[str, Any]] = field(default_factory=list)

    # --- User profile ---
    user_profile: dict[str, Any] | None = None

    # --- Platform context (WhatsApp, mobile, Telegram, etc.) ---
    platform: str = "mobile"                    # identifies the inbound channel
    platform_user_id: str = ""                  # phone number, chat ID, etc.
    media_attachments: list[str] = field(default_factory=list)  # pre-signed media URLs

    def to_service_ctx(self) -> dict[str, str]:
        """Return the context forwarded as HTTP headers to Java services.

        Maps exactly to the keyword args BaseServiceClient._request() accepts:
        request_id and workflow_id only.

        NOTE: user_id is NOT included here — each client method already receives
        it as a positional argument (e.g. get_account_by_user_id(user_id, **ctx)).
        Including it here would cause a 'multiple values for argument' TypeError.
        """
        return {
            "request_id": self.request_id,
            "workflow_id": self.session_id,
            "session_id": self.session_id,
        }
