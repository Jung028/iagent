import structlog

from iagent.api.schemas.chat import ChatResponse
from iagent.core.context.models import AgentContext
from iagent.core.orchestrator.agents.plan import ActionType, ExecutionPlan, PlanStep
from iagent.core.orchestrator.agents.planning_agent import PlanningAgent
from iagent.core.orchestrator.agents.read_agent import ReadAgent
from iagent.core.orchestrator.agents.write_agent import WriteAgent
from iagent.core.orchestrator.agents.voice_agent import VoiceAgent
from iagent.core.orchestrator.result import OrchestratorResult

log = structlog.get_logger(__name__)

_PENDING_KEY = "pending_plan"
_PENDING_PIN_KEY = "pending_pin"

_CANCEL_PHRASES = frozenset({
    "cancel", "stop", "abort", "no", "nope", "never mind", "nevermind",
    "quit", "exit", "don't", "dont", "back", "go back",
})


class Orchestrator:
    """Three-phase orchestrator matching the agent sequence diagram.

    Phase 1 — Planning  : PlanningAgent decomposes the user message into ordered steps.
    Phase 2 — Execution : ReadAgent fetches data; WriteAgent executes mutations
                          (each write step requires explicit user confirmation first).
    Phase 3 — Synthesis : VoiceAgent turns all raw results into a friendly reply.
    """

    def __init__(
        self,
        planning_agent: PlanningAgent,
        read_agent: ReadAgent,
        write_agent: WriteAgent,
        voice_agent: VoiceAgent,
        account_client: object,
        business_client: object,
        user_client: object,
        session_store: object | None = None,
    ) -> None:
        self._planning      = planning_agent
        self._read          = read_agent
        self._write         = write_agent
        self._voice         = voice_agent
        self._account_client  = account_client
        self._business_client = business_client
        self._user_client     = user_client
        self._session_store   = session_store

    # ── Entry point ───────────────────────────────────────────────────────────

    async def run(self, ctx: AgentContext) -> ChatResponse:
        clients = {
            "account_client":  self._account_client,
            "business_client": self._business_client,
            "user_client":     self._user_client,
        }

        # PIN submitted → complete the transfer (Step 2 of transferInit → transferConfirm)
        pending_pin = await self._session_store.get_state(ctx.session_id, _PENDING_PIN_KEY) \
            if self._session_store and ctx.session_id else None
        if pending_pin and ctx.entities.get("pin"):
            return await self._complete_with_pin(ctx, pending_pin, clients)

        # Handle a pending write step that is awaiting user confirmation
        pending = await self._get_pending(ctx)
        if pending:
            if _is_cancellation(ctx.raw_message):
                await self._clear_pending(ctx)
                log.info("orchestrator_pending_cancelled")
                return OrchestratorResult(
                    intent=ctx.intent,
                    ui={"type": "text_response", "message": "Action cancelled. How else can I help?"},
                    requires_action=False,
                ).to_chat_response()

            if ctx.entities.get("confirmed"):
                return await self._resume_after_confirmation(ctx, pending, clients)

            # User sent an unrelated message while a write action awaits confirmation.
            # Re-present the confirmation card — do NOT start a new plan.
            step = _deserialize_plan(pending["plan"]).steps[pending["pending_step_index"]]
            log.info("orchestrator_pending_reminder", action=step.action_type)
            return self._pending_reminder(ctx, step).to_chat_response()

        # ── Phase 1: Planning ─────────────────────────────────────────────────
        plan = await self._planning.create_plan(ctx)
        log.info("orchestrator_plan", steps=[s.action_type for s in plan.steps])

        # ── Phase 2: Execution ────────────────────────────────────────────────
        results: list[dict] = []

        for step in plan.steps:
            if step.action_type == ActionType.GREETING:
                results.append({"step": "greeting", "data": None})
                continue

            if step.is_read:
                data = await self._read.execute_step(step, ctx, **clients)
                results.append({"step": step.action_type, "data": data})
                continue

            if step.is_write:
                # Gate: store plan state and ask for user confirmation
                await self._save_pending(ctx, plan, results, plan.steps.index(step))
                return self._confirmation_response(ctx, step).to_chat_response()

        # ── Phase 3: Synthesis ────────────────────────────────────────────────
        result = await self._voice.synthesize(ctx, plan, results)
        return result.to_chat_response()

    # ── Confirmation flow ─────────────────────────────────────────────────────

    async def _resume_after_confirmation(
        self,
        ctx: AgentContext,
        pending: dict,
        clients: dict,
    ) -> ChatResponse:
        plan         = _deserialize_plan(pending["plan"])
        results      = pending["results"]
        step_index   = pending["pending_step_index"]
        step         = plan.steps[step_index]

        log.info("orchestrator_confirmed_write", action=step.action_type)

        # Execute the confirmed write step (Step 1 — transferInit)
        data = await self._write.execute_step(step, ctx, **clients)

        # transferInit succeeded — save transferToken and return PIN card
        if data.get("status") == "awaiting_pin":
            await self._save_pending_pin(ctx, data, plan, results)
            return self._pin_input_response(ctx, data).to_chat_response()

        results.append({"step": step.action_type, "data": data})

        # Continue with any remaining steps after the confirmed write
        for next_step in plan.steps[step_index + 1:]:
            if next_step.is_write:
                await self._save_pending(ctx, plan, results, plan.steps.index(next_step))
                return self._confirmation_response(ctx, next_step).to_chat_response()
            if next_step.is_read:
                read_data = await self._read.execute_step(next_step, ctx, **clients)
                results.append({"step": next_step.action_type, "data": read_data})

        await self._clear_pending(ctx)

        # Phase 3: Synthesize final response
        result = await self._voice.synthesize(ctx, plan, results)
        return result.to_chat_response()

    async def _complete_with_pin(
        self,
        ctx: AgentContext,
        pending_pin: dict,
        clients: dict,
    ) -> ChatResponse:
        """Step 2 of transfer: user submitted PIN → call transferConfirm."""
        pin = ctx.entities["pin"]
        log.info("orchestrator_pin_received", action=pending_pin.get("action"))

        data = await self._write.execute_confirm_pin(pending_pin, pin, ctx, **clients)

        # Clear PIN state
        if self._session_store and ctx.session_id:
            await self._session_store.del_state(ctx.session_id, _PENDING_PIN_KEY)

        # Reconstruct the plan to pass to VoiceAgent for synthesis
        plan = _deserialize_plan(pending_pin["plan"])
        results: list[dict] = pending_pin.get("results_so_far", [])
        results.append({"step": pending_pin.get("action"), "data": data})

        result = await self._voice.synthesize(ctx, plan, results)
        return result.to_chat_response()

    async def _save_pending_pin(
        self,
        ctx: AgentContext,
        write_data: dict,
        plan: ExecutionPlan,
        results_so_far: list[dict],
    ) -> None:
        if not self._session_store or not ctx.session_id:
            return
        await self._session_store.set_state(
            ctx.session_id,
            _PENDING_PIN_KEY,
            {
                **write_data,
                "plan":           _serialize_plan(plan),
                "results_so_far": results_so_far,
            },
        )

    def _pin_input_response(self, ctx: AgentContext, write_data: dict) -> OrchestratorResult:
        return OrchestratorResult(
            intent=ctx.intent,
            ui={
                "type":    "pin_input_card",
                "message": write_data.get("message", "Enter your PIN to authorise this transaction."),
                "action":  write_data.get("action", ""),
            },
            requires_action=True,
        )

    def _pending_reminder(self, ctx: AgentContext, step: PlanStep) -> OrchestratorResult:
        """Re-present the confirmation card when the user sends an unrelated message mid-flow."""
        p = step.params
        if step.action_type == ActionType.WRITE_TRANSFER:
            amount = p.get("amount") or ctx.entities.get("amount", "?")
            payee  = p.get("payeeName") or ctx.entities.get("payeeName", "recipient")
            msg = f"You have a pending transfer of RM {amount} to {payee}. Please confirm or say 'cancel' to abort."
        elif step.action_type == ActionType.WRITE_TOP_UP:
            amount = p.get("amount") or ctx.entities.get("amount", "?")
            msg = f"You have a pending top-up of RM {amount}. Please confirm or say 'cancel' to abort."
        else:
            msg = f"You have a pending action: {step.description}. Please confirm or say 'cancel' to abort."

        return OrchestratorResult(
            intent=ctx.intent,
            ui={"type": "confirmation_card", "message": msg, "action": step.action_type},
            requires_action=True,
        )

    def _confirmation_response(
        self, ctx: AgentContext, step: PlanStep
    ) -> OrchestratorResult:
        p = step.params
        if step.action_type == ActionType.WRITE_TRANSFER:
            amount = p.get("amount") or ctx.entities.get("amount", "?")
            payee  = p.get("payeeName") or ctx.entities.get("payeeName", "recipient")
            msg    = f"Confirm transfer of RM {amount} to {payee}?"
        elif step.action_type == ActionType.WRITE_TOP_UP:
            amount = p.get("amount") or ctx.entities.get("amount", "?")
            msg    = f"Confirm top-up of RM {amount}?"
        else:
            msg = f"Confirm: {step.description}?"

        return OrchestratorResult(
            intent=ctx.intent,
            ui={"type": "confirmation_card", "message": msg, "action": step.action_type},
            requires_action=True,
        )

    # ── Session state helpers ─────────────────────────────────────────────────

    async def _save_pending(
        self,
        ctx: AgentContext,
        plan: ExecutionPlan,
        results: list[dict],
        step_index: int,
    ) -> None:
        if not self._session_store or not ctx.session_id:
            return
        await self._session_store.set_state(
            ctx.session_id,
            _PENDING_KEY,
            {
                "plan":                _serialize_plan(plan),
                "results":             results,
                "pending_step_index":  step_index,
            },
        )

    async def _get_pending(self, ctx: AgentContext) -> dict | None:
        if not self._session_store or not ctx.session_id:
            return None
        return await self._session_store.get_state(ctx.session_id, _PENDING_KEY)

    async def _clear_pending(self, ctx: AgentContext) -> None:
        if self._session_store and ctx.session_id:
            await self._session_store.del_state(ctx.session_id, _PENDING_KEY)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _is_cancellation(message: str) -> bool:
    return message.strip().lower() in _CANCEL_PHRASES


# ── Plan serialisation ────────────────────────────────────────────────────────

def _serialize_plan(plan: ExecutionPlan) -> dict:
    return {
        "raw_intent": plan.raw_intent,
        "steps": [
            {
                "action_type": s.action_type,
                "description": s.description,
                "params":      s.params,
            }
            for s in plan.steps
        ],
    }


def _deserialize_plan(data: dict) -> ExecutionPlan:
    steps = [
        PlanStep(
            action_type=ActionType(s["action_type"]),
            description=s["description"],
            params=s.get("params") or {},
        )
        for s in data["steps"]
    ]
    return ExecutionPlan(steps=steps, raw_intent=data.get("raw_intent", ""))
