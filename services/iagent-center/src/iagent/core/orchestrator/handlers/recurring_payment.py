import structlog
from typing import Any

from iagent.core.context.models import AgentContext
from iagent.core.orchestrator.handlers.base import ToolHandler
from iagent.core.orchestrator.result import OrchestratorResult
from iagent.core.response_builder.builder import build_error_response
from iagent.core.intent.models import Intent

log = structlog.get_logger(__name__)


class RecurringPaymentHandler(ToolHandler):
    """Handles Intent.RECURRING_PAYMENT.

    Lets users set up, list, or cancel scheduled payments via natural language.
    e.g. "pay rent RM1500 to 01234567 every 1st of the month"
    """

    async def execute(self, ctx: AgentContext, **clients: Any) -> OrchestratorResult:
        # TODO: extract entities from ctx.entities:
        #   - recipient_account / phone
        #   - amount + currency
        #   - frequency (monthly / weekly) + day_of_month
        #   - reference / description

        # TODO: call IBusinessClient.create_scheduled_payment(...)
        # TODO: if ctx.entities has no amount → return ConfirmationCard asking for missing fields (slot-filling)
        # TODO: on success → return RecurringPaymentCard with schedule summary
        # TODO: on error → return ErrorCard

        response = build_error_response(
            intent=Intent.RECURRING_PAYMENT,
            code="not_implemented",
            message="Recurring payments are coming soon.",
        )
        return OrchestratorResult(intent=Intent.RECURRING_PAYMENT, ui=response.ui)
