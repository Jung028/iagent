import structlog

from iagent.core.models.intent import Intent

log = structlog.get_logger(__name__)


class IntentRouter:
    """Maps an Intent value to the correct ToolHandler.

    Replaces the if/else block in chat.py.
    Handlers are registered at startup via register().
    Unrecognised intents fall through to FallbackHandler.
    """

    def __init__(self) -> None:
        self._handlers: dict[str, object] = {}

        from iagent.core.orchestrator.handlers.fallback import FallbackHandler
        self._fallback = FallbackHandler()

    def register(self, intent: Intent, handler: object) -> None:
        """Bind an Intent to its handler. Called once during app startup."""
        if intent.value in self._handlers:
            raise ValueError(
                f"Handler already registered for intent '{intent.value}'. "
                "Each intent may only have one handler."
            )
        self._handlers[intent.value] = handler

    def resolve(self, intent: str) -> object:
        """Return the handler for intent, or FallbackHandler if unregistered."""
        handler = self._handlers.get(intent)
        if handler is None:
            log.warning("intent_router_fallback", intent=intent)
        return handler or self._fallback
