import structlog
from typing import Any

from iagent.core.orchestrator.handlers.base import ToolHandler
from iagent.core.context.models import AgentContext
from iagent.core.orchestrator.result import OrchestratorResult
from iagent.core.tools.transaction_details import handle as transaction_handle
from iagent.core.response_builder.builder import build_error_response, build_transaction_details_response
from iagent.core.models.intent import Intent

log = structlog.get_logger(__name__)

class TransactionDetailsInquiryHandler(ToolHandler):
    """To handle transaction details queries"""

    async def execute(
            self, 
            ctx:AgentContext,
            **clients: Any,
    ) -> OrchestratorResult:
        
        try : 
            # reuse the account id from the context 
            extra: dict[str, Any] = {}
            if "account_id" in ctx.entities: 
                extra["account_id"] = ctx.entities["account_id"]
 
            transaction_id = ctx.entities.get("transaction_id")
            print(transaction_id)
   
            transaction_details = await transaction_handle(
                user_id=ctx.user_id,
                transaction_id=transaction_id,
                account_client=clients["account_client"],
                business_client=clients["business_client"],
                user_client=clients["user_client"],
                **ctx.to_service_ctx()
            ) 
            response = build_transaction_details_response(transaction_details)
            return OrchestratorResult(
                intent=Intent.TRANSACTION_DETAILS,
                ui=response.ui,
                requires_action=response.requires_action,
            )
        except Exception as exc: 
            log.exception("transaction_details_inquiry_failed", user_id=ctx.user_id, error=str(exc))
            response = build_error_response(
                intent=Intent.TRANSACTION_DETAILS,
                code="transaction_details_inquiry_failed",
                message="Unable to fetch the transaction details, please try again later",
            )
            return OrchestratorResult(
                intent=Intent.TRANSACTION_DETAILS,
                ui=response.ui,
                requires_action=False,
            )

