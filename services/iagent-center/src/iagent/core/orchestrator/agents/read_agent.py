import structlog

from iagent.core.context.models import AgentContext
from iagent.core.orchestrator.agents.plan import ActionType, PlanStep

log = structlog.get_logger(__name__)


class ReadAgent:
    """Researcher agent — executes read-only operations against the ledger/database.

    Takes a specific PlanStep and executes the appropriate tool, returning raw data.
    No LLM loop — direct tool invocation only.
    """

    async def execute_step(
        self,
        step: PlanStep,
        ctx: AgentContext,
        **clients,
    ) -> dict:
        log.info("read_agent_execute", action=step.action_type)

        if step.action_type == ActionType.READ_BALANCE:
            return await self._get_balance(ctx, clients)

        if step.action_type == ActionType.READ_TRANSACTIONS:
            return await self._get_transactions(step, ctx, clients)

        return {"error": f"Unknown read action: {step.action_type}"}

    async def _get_balance(self, ctx: AgentContext, clients: dict) -> dict:
        from iagent.core.tools import balance
        try:
            result = await balance.handle(
                user_id=ctx.user_id,
                account_client=clients["account_client"],
                business_client=clients["business_client"],
                user_client=clients["user_client"],
                **ctx.to_service_ctx(),
            )
            log.info("read_balance_ok", accounts=len(result))
            return {"accounts": result}
        except Exception as exc:
            log.warning("read_balance_failed", error=str(exc))
            return {"error": str(exc)}

    async def _get_transactions(
        self, step: PlanStep, ctx: AgentContext, clients: dict
    ) -> dict:
        from iagent.core.tools import transaction_history
        try:
            params = dict(step.params)
            transactions = await transaction_history.handle(
                user_id=ctx.user_id,
                phone_no=ctx.platform_user_id,
                account_client=clients["account_client"],
                business_client=clients["business_client"],
                user_client=clients["user_client"],
                params=params,
                user_profile=ctx.user_profile,
                **ctx.to_service_ctx(),
            )
            log.info("read_transactions_ok", count=len(transactions))
            return {"transactions": transactions}
        except Exception as exc:
            log.warning("read_transactions_failed", error=str(exc))
            return {"error": str(exc)}


# Backward-compatibility alias — existing imports of TransactionReadAgent still work.
TransactionReadAgent = ReadAgent
