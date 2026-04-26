import structlog
from typing import Any

from iagent.core.context.models import AgentContext
from iagent.core.orchestrator.handlers.base import ToolHandler
from iagent.core.orchestrator.result import OrchestratorResult
from iagent.core.tools.balance import handle as balance_handle
from iagent.core.response_builder.builder import build_balance_response, build_error_response
from iagent.core.models.intent import Intent

log = structlog.get_logger(__name__)


class BalanceInquiryHandler(ToolHandler):
    """Handles Intent.BALANCE_INQUIRY."""

    async def execute(
        self,
        ctx: AgentContext,
        **clients: Any,
    ) -> OrchestratorResult:
        try:
            # If the classifier already extracted an account_id, pass it directly
            # so balance.handle() can skip the account-lookup step.
            extra: dict[str, Any] = {}
            if "account_id" in ctx.entities:
                extra["account_id"] = ctx.entities["account_id"]

            accounts = await balance_handle(
                user_id=ctx.user_id,
                account_client=clients["account_client"],
                business_client=clients["business_client"],
                user_client=clients["user_client"],
                **ctx.to_service_ctx(),
                **extra,
            )
            response = build_balance_response(accounts)
            return OrchestratorResult(
                intent=Intent.BALANCE_INQUIRY,
                ui=response.ui,
                requires_action=response.requires_action,
            )
        except Exception as exc:
            log.exception("balance_inquiry_failed", user_id=ctx.user_id, error=str(exc))
            response = build_error_response(
                intent=Intent.BALANCE_INQUIRY,
                code="balance_fetch_failed",
                message="Unable to retrieve your balance right now. Please try again.",
            )
            return OrchestratorResult(
                intent=Intent.BALANCE_INQUIRY,
                ui=response.ui,
                requires_action=False,
            )
