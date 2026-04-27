from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentContext:
    # --- Identity (Required) ---
    user_id: str
    request_id: str
    session_id: str

    # --- LLM output (Required) ---
    raw_message: str
    intent: str
    confidence: float

    # --- Fields with Defaults ---
    auth_token: str | None = None
    entities: dict[str, Any] = field(default_factory=dict)
    history: list[dict[str, Any]] = field(default_factory=list)
    user_profile: dict[str, Any] | None = None
    platform: str = "mobile"
    platform_user_id: str = ""
    media_attachments: list[str] = field(default_factory=list)

    def to_service_ctx(self) -> dict[str, str]:
        """Return the context forwarded as HTTP headers to Java services."""
        ctx = {
            "request_id": self.request_id,
            "workflow_id": self.session_id,
            "session_id": self.session_id,
        }
        if self.auth_token:
            ctx["auth_token"] = self.auth_token
        return ctx
