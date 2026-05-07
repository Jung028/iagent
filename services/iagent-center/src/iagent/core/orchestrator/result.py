from dataclasses import dataclass, field
from typing import Any

from iagent.api.schemas.chat import ChatResponse


@dataclass
class OrchestratorResult:
    """Structured return value from a ToolHandler.

    Decouples tool execution output from ChatResponse serialisation.
    """

    intent: str
    ui: Any  # AnyUICard — typed as Any to avoid circular imports
    requires_action: bool = False
    requires_followup: bool = False
    followup_context: dict[str, Any] = field(default_factory=dict)

    def to_chat_response(self) -> ChatResponse:
        return ChatResponse(
            intent=self.intent,
            ui=self.ui,
            requires_action=self.requires_action,
        )
