import structlog
from typing import Any

from iagent.core.context.models import AgentContext
from iagent.core.orchestrator.handlers.base import ToolHandler
from iagent.core.orchestrator.result import OrchestratorResult
from iagent.core.response_builder.builder import build_error_response
from iagent.core.models.intent import Intent

log = structlog.get_logger(__name__)


class ExpenseTrackingHandler(ToolHandler):
    """Handles Intent.EXPENSE_TRACKING.

    Lets users query, categorise, and export their spending history.
    e.g. "how much did I spend on food last month"
    """

    async def execute(self, ctx: AgentContext, **clients: Any) -> OrchestratorResult:
        # TODO: extract entities: date_range, category, merchant

        # TODO: call IBusinessClient.query_transactions(account_id, date_range, category)
        # TODO: aggregate by category and return ExpenseCard (new UI card to add)
        # TODO: support "export to CSV" intent variant → generate file and return download URL

        response = build_error_response(
            intent=Intent.EXPENSE_TRACKING,
            code="not_implemented",
            message="Expense tracking is coming soon.",
        )
        return OrchestratorResult(intent=Intent.EXPENSE_TRACKING, ui=response.ui)
