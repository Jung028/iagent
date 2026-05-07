import uuid
import structlog

from iagent.core.context.models import AgentContext
from iagent.core.orchestrator.agents.plan import ActionType, PlanStep

log = structlog.get_logger(__name__)


class WriteAgent:
    """Executor agent — carries out write operations (money movement).

    Transfer flow is two-step:
      1. execute_transfer_init  → calls transferInit, returns {"status": "awaiting_pin", ...}
      2. execute_transfer_confirm → calls transferConfirm with user PIN, returns success result
    """

    # ── Public entry points ───────────────────────────────────────────────────

    async def execute_step(
        self,
        step: PlanStep,
        ctx: AgentContext,
        **clients,
    ) -> dict:
        """Step 1 of a write action: called after user clicks Confirm."""
        log.info("write_agent_init", action=step.action_type)

        if step.action_type == ActionType.WRITE_TRANSFER:
            return await self._transfer_init(step, ctx, **clients)

        if step.action_type == ActionType.WRITE_TOP_UP:
            return await self._top_up_init(step, ctx, **clients)

        return {"error": f"Unknown write action: {step.action_type}"}

    async def execute_confirm_pin(
        self,
        pending: dict,
        pin: str,
        ctx: AgentContext,
        **clients,
    ) -> dict:
        """Step 2: called when the user submits their PIN from the PinInputCard."""
        action = pending.get("action")
        log.info("write_agent_confirm_pin", action=action)

        if action == ActionType.WRITE_TRANSFER:
            return await self._transfer_confirm(pending, pin, ctx, **clients)

        return {"error": f"PIN confirm not supported for action: {action}"}

    # ── Transfer ──────────────────────────────────────────────────────────────

    async def _transfer_init(
        self, step: PlanStep, ctx: AgentContext, **clients
    ) -> dict:
        amount   = step.params.get("amount") or ctx.entities.get("amount")
        payee    = step.params.get("payeeName") or ctx.entities.get("payeeName", "recipient")
        currency = step.params.get("currency", "MYR")

        try:
            account_client  = clients["account_client"]
            business_client = clients["business_client"]
            service_ctx     = ctx.to_service_ctx()

            # Resolve payer account ID
            payer_account = await account_client.get_account_by_user_id(ctx.user_id, **service_ctx)
            payer_account_id = payer_account["accountId"]

            # Resolve payee account ID
            # Use explicit account number if provided; otherwise contact lookup is required
            payee_account_id = step.params.get("payeeAccountNo") or ctx.entities.get("payeeAccountNo")
            if not payee_account_id:
                # TODO: resolve payee name → userId → accountId via IUserClient contacts
                raise ValueError(
                    f"Cannot resolve account for '{payee}'. "
                    "Ask the user to provide an account number."
                )

            transfer_token = await business_client.transfer_init(
                payer_account_id=payer_account_id,
                payee_account_id=payee_account_id,
                amount=float(amount),
                currency=currency,
                unique_request_id=str(uuid.uuid4()),
                **service_ctx,
            )

            log.info("transfer_init_ok", payee=payee, amount=amount)
            return {
                "status":         "awaiting_pin",
                "action":         ActionType.WRITE_TRANSFER,
                "transfer_token": transfer_token,
                "payer_account_id": payer_account_id,
                "amount":         amount,
                "currency":       currency,
                "payee":          payee,
                "message":        f"Enter your 6-digit PIN to authorise the RM {amount} transfer to {payee}.",
            }

        except Exception as exc:
            log.warning("transfer_init_failed", error=str(exc))
            return {"error": str(exc)}

    async def _transfer_confirm(
        self, pending: dict, pin: str, ctx: AgentContext, **clients
    ) -> dict:
        try:
            business_client  = clients["business_client"]
            service_ctx      = ctx.to_service_ctx()

            result = await business_client.transfer_confirm(
                account_id=pending["payer_account_id"],
                password=pin,
                transfer_token=pending["transfer_token"],
                **service_ctx,
            )
            log.info("transfer_confirm_ok", txid=result.get("txid"))
            return {**result, "payee": pending.get("payee")}

        except Exception as exc:
            log.warning("transfer_confirm_failed", error=str(exc))
            return {"error": str(exc)}

    # ── Top-up ────────────────────────────────────────────────────────────────

    async def _top_up_init(
        self, step: PlanStep, ctx: AgentContext, **clients
    ) -> dict:
        amount   = step.params.get("amount") or ctx.entities.get("amount")
        currency = step.params.get("currency", "MYR")
        # TODO: wire to TopUp backend flow (Stripe intent creation)
        log.info("top_up_stub", amount=amount)
        return {
            "status":   "success",
            "action":   "top_up",
            "amount":   amount,
            "currency": currency,
            "txid":     "TOP_STUB",
        }
