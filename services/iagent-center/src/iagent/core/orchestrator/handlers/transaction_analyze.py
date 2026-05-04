from typing import Any

import structlog

from iagent.core.context.models import AgentContext
from iagent.core.models.intent import Intent
from iagent.core.orchestrator.handlers.base import ToolHandler
from iagent.core.orchestrator.mapper.mapper import map_entities_to_api_params
from iagent.core.orchestrator.result import OrchestratorResult
from iagent.core.response_builder.builder import build_error_response, build_transaction_analysis_response
from iagent.core.tools.transaction_history import handle as transaction_history_handle

log = structlog.get_logger(__name__)


class TransactionAnalyzeInquiryHandler(ToolHandler):
    """
    Pipeline: iWallet fetch → Planner → Analyzer → LLM summary → response

    The Planner decomposes the user's question into structured tasks.
    The Analyzer executes those tasks against the fetched transactions,
    using Python for maths and Gemini for the natural language summary.
    This is the RAG augmented-generation step.
    """

    async def execute(
        self,
        ctx: AgentContext,
        **clients: Any,
    ) -> OrchestratorResult:
        params = ctx.entities

        # 1. RETRIEVAL — fetch transactions from iWallet
        transactions = await transaction_history_handle(
            user_id=ctx.user_id,
            phone_no=ctx.platform_user_id,
            account_client=clients["account_client"],
            business_client=clients["business_client"],
            user_client=clients["user_client"],
            params=params,
            user_profile=ctx.user_profile,  
            **ctx.to_service_ctx(),
        )

        if not transactions:
            error = build_error_response(
                intent=Intent.TRANSACTION_ANALYZE,
                code="no_transactions_found",
                message="No transactions found for the requested period.",
            )
            return OrchestratorResult(
                intent=error.intent,
                ui=error.ui,
                requires_action=error.requires_action,
            )

        log.info("transactions_fetched", count=len(transactions))

        response = build_transaction_analysis_response(transactions)

        return OrchestratorResult(
            intent=response.intent,
            ui=response.ui,
            requires_action=response.requires_action,
        )
