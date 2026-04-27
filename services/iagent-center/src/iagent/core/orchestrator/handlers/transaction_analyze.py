


from typing import Any

from iagent.core.context.models import AgentContext
from iagent.core.models.intent import Intent
from iagent.core.orchestrator.handlers.base import ToolHandler
from iagent.core.orchestrator.mapper.mapper import map_entities_to_api_params
from iagent.core.orchestrator.result import OrchestratorResult
from iagent.core.response_builder.builder import build_error_response, build_transaction_history_response
from iagent.core.response_builder.card_factory import make_error_card
from iagent.core.tools.transaction_history import handle as transaction_history_handle


class TransactionAnalyzeInquiryHandler(ToolHandler):
    async def execute(
            self,
            ctx:AgentContext,
            **clients:Any,
    ) -> OrchestratorResult:
        # first, we handle,
        entities = ctx.entities
        params = map_entities_to_api_params(entities)

        # then we build response based on the result dict[] or other patterns
        transaction_history_list = await transaction_history_handle(
            #what do you need? 
            user_id=ctx.user_id,
            phone_no=ctx.platform_user_id,
            account_client=clients["account_client"],
            business_client=clients["business_client"],
            user_client=clients["user_client"],
            params=params,
            **ctx.to_service_ctx(),
        )

        response = build_error_response(
            intent=Intent.TRANSACTION_ANALYZE,
            #TODO: add enumß
            code="TXN_HIST_NOTß",
            message="transaction history not found",
        )
        if not transaction_history_list:
            return OrchestratorResult(
                intent=response.intent,
                ui=response.ui,
                requires_action=response.requires_action
            )
            

        #build the transaction history response list 
        result=build_transaction_history_response(transaction_history_list)
        
        return OrchestratorResult(
            intent=Intent.TRANSACTION_ANALYZE,
            ui=result.ui,
            requires_action=result.requires_action,
        )