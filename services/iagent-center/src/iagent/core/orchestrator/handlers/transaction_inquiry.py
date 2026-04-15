import structlog
from typing import Any

from iagent.core.orchestrator.handlers.base import ToolHandler
from iagent.core.context.models import AgentContext
from iagent.core.orchestrator.result import OrchestratorResult
from iagent.core.tools.transaction import handle as transaction_handle
from iagent.core.response_builder.builder import build_error_response, build_transaction_details_response
from iagent.core.intent.models import Intent

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

            # there is an issue with using the entities as the way to retrieve the accountId and the txnId, 
            # because lets say the user enters the prompt, "display my transaction details", but he doesnt know that we 
            # first need to know what is the transaction id,which is essential to know when we want to queryTransactionDetails. 
            # so there needs to be a follow up questions, to ask user which transaction you want to know about, so we need to get the context and place in entity. 
            # so there needs to be essential keywords to be met 

            
            txnId = ctx.entities.get("txn_id")
            print(txnId)

            transaction_details = await transaction_handle(
                user_id=ctx.user_id,
                transaction_id=txnId,
                account_client=clients["account_client"],
                business_client=clients["business_client"],
                **ctx.to_service_ctx()
            ) 
            response = build_transaction_details_response(transaction_details)
            return OrchestratorResult(
                intent=Intent.TRANSACTION_DETAILS_INQUIRY,
                ui=response.ui,
                requires_action=response.requires_action,
            )
        except Exception as exc: 
            log.exception("transaction_details_inquiry_failed", user_id=ctx.user_id, error=str(exc))
            response = build_error_response(
                intent=Intent.TRANSACTION_DETAILS_INQUIRY,
                code="transaction_details_inquiry_failed",
                message="Unable to fetch the transaction details, please try again later",
            )
            return OrchestratorResult(
                intent=Intent.TRANSACTION_DETAILS_INQUIRY,
                ui=response.ui,
                requires_action=False,
            )

