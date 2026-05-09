

from typing import Any

from iagent.core.context.models import AgentContext
from iagent.core.orchestrator.handlers.base import ToolHandler
from iagent.core.orchestrator.result import OrchestratorResult
from iagent.core.response_builder.builder import build_error_response, build_transaction_search_response
from iagent.core.tools.transaction_history import handle as transaction_history_handle


class TransctionSearchInquiryHandler(ToolHandler): 
    """
    Handler for normal search of transaction 
    """
    async def execute(
            self,
            ctx: AgentContext,
            **clients: Any,
    ) -> OrchestratorResult: 
        
        # handle transaction search 
        transactions = await transaction_history_handle(
            user_id=ctx.user_id,
            phone_no=ctx.platform_user_id,
            account_client=clients["account_client"],
            business_client=clients["business_client"],
            user_client=clients["user_client"],
            params=ctx.entities,
            user_profile=ctx.user_profile,
            **ctx.to_service_ctx(),
        )
        
        # if not transactions, return error 
        if not transactions: 

            error = build_error_response(
                intent=ctx.intent,
                code="transaction_search_failed",
                message="No transactions found"
            )
            return OrchestratorResult(
                intent=error.intent,
                ui=error.ui,
                requires_action=False,
            )

        # else, build response,
        response = build_transaction_search_response(transactions)

        # return orchestrator result 
        return OrchestratorResult(
            intent=ctx.intent, 
            ui=response.ui,
            requires_action=False,
        )

    