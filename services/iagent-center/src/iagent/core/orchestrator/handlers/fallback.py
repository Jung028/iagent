from typing import Any

from iagent.core.context.models import AgentContext
from iagent.core.orchestrator.handlers.base import ToolHandler
from iagent.core.orchestrator.result import OrchestratorResult
from iagent.core.response_builder.builder import build_error_response


class FallbackHandler(ToolHandler):
    """Handles any intent that has no registered handler.

    Returns a user-facing ErrorCard with code "unsupported_intent".
    """

    async def execute(
        self,
        ctx: AgentContext,
        **clients: Any,
    ) -> OrchestratorResult:
        # TODO: use ctx.intent in the error message for clearer mobile UX
        # TODO: emit intent_total metric with label unsupported=True
        response = build_error_response(
            intent=ctx.intent,
            code="unsupported_intent",
            message="Unsupported, Please contact developer to help develop the feature",
        )
        return OrchestratorResult(
            intent=ctx.intent,
            ui=response.ui,
            requires_action=False,
        )
