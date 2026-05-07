import anthropic
import structlog

from iagent.core.context.models import AgentContext
from iagent.core.orchestrator.agents.plan import ActionType, ExecutionPlan, PlanStep

log = structlog.get_logger(__name__)

MODEL = "claude-haiku-4-5"

CREATE_PLAN_TOOL = {
    "name": "create_plan",
    "description": (
        "Decompose the user's request into an ordered list of actions. "
        "Each action maps to a specific agent that will execute it."
    ),
    "input_schema": {
        "type": "object",
        "required": ["steps"],
        "properties": {
            "steps": {
                "type": "array",
                "description": "Ordered list of actions to execute.",
                "items": {
                    "type": "object",
                    "required": ["action_type", "description"],
                    "properties": {
                        "action_type": {
                            "type": "string",
                            "enum": [
                                "greeting",
                                "read_balance",
                                "read_transactions",
                                "write_transfer",
                                "write_top_up",
                            ],
                        },
                        "description": {
                            "type": "string",
                            "description": "What this step does in plain English.",
                        },
                        "params": {
                            "type": "object",
                            "description": (
                                "Structured parameters for this step. "
                                "write_transfer: {amount, payeeName, currency}. "
                                "write_top_up: {amount, currency}. "
                                "read_transactions: {pageSize, sortOrder, gmtCreateStart, gmtCreateEnd, payeeName}."
                            ),
                        },
                    },
                },
            }
        },
    },
}

SYSTEM_PROMPT = """\
You are the Planning Agent (Architect) for iAgent, an eWallet assistant.
Your ONLY job is to decompose the user's request into an ordered execution plan.
Always call create_plan. Never respond in plain text.

ACTION TYPES:
  greeting          — user said hi/hello/how are you, or the message is casual chat
  read_balance      — user wants to know their wallet balance
  read_transactions — user wants to see, search, or analyse transaction history
  write_transfer    — user wants to send or transfer money to someone
  write_top_up      — user wants to add money to their wallet

RULES:
- A single message may produce multiple steps.
  Example: "Hello, buy boba and check balance" → [greeting, read_balance, write_transfer]
- Greetings are always first when the message is conversational.
- Read steps come before write steps where possible (data is available for confirmation).
- A purely greeting/conversational message → [greeting] only.
- Extract params for write actions: amount, payeeName, currency (default MYR).
- For read_transactions include query params (pageSize, sortOrder, date ranges, payeeName filter).

EXAMPLES:
  "Hello, buy boba and check balance"  → [greeting, read_balance, write_transfer(item=boba, amount=5)]
  "What is my balance?"                → [read_balance]
  "Transfer RM50 to Ali"               → [write_transfer(amount=50, payeeName=Ali, currency=MYR)]
  "Hi"                                 → [greeting]
  "Show me my last 5 transactions"     → [read_transactions(pageSize=5, sortOrder=DESC)]
  "Top up RM100"                       → [write_top_up(amount=100, currency=MYR)]
"""


class PlanningAgent:
    """Architect agent — decomposes user requests into an ordered execution plan."""

    def __init__(self, client: anthropic.AsyncAnthropic) -> None:
        self._client = client

    async def create_plan(self, ctx: AgentContext) -> ExecutionPlan:
        try:
            response = await self._client.messages.create(
                model=MODEL,
                max_tokens=512,
                system=SYSTEM_PROMPT,
                tools=[CREATE_PLAN_TOOL],
                tool_choice={"type": "any"},
                messages=[{"role": "user", "content": ctx.raw_message}],
            )

            for block in response.content:
                if block.type == "tool_use" and block.name == "create_plan":
                    return self._build_plan(block.input, ctx.raw_message)

        except Exception as exc:
            log.warning("planning_agent_failed", error=str(exc))

        return self._fallback_plan(ctx)

    def _build_plan(self, args: dict, raw_intent: str) -> ExecutionPlan:
        steps = []
        for raw in args.get("steps", []):
            try:
                action_type = ActionType(raw.get("action_type", ""))
            except ValueError:
                log.warning("unknown_action_type", value=raw.get("action_type"))
                continue
            steps.append(PlanStep(
                action_type=action_type,
                description=raw.get("description", ""),
                params=raw.get("params") or {},
            ))

        if not steps:
            steps = [PlanStep(ActionType.GREETING, "Greet the user")]

        log.info("plan_created", steps=[s.action_type for s in steps])
        return ExecutionPlan(steps=steps, raw_intent=raw_intent)

    def _fallback_plan(self, ctx: AgentContext) -> ExecutionPlan:
        """Derive a single-step plan from the IntentClassifier result as a safe fallback."""
        from iagent.core.models.intent import Intent

        intent = ctx.intent
        if intent == Intent.TRANSFER:
            steps = [PlanStep(ActionType.WRITE_TRANSFER, "Transfer money", dict(ctx.entities))]
        elif intent == Intent.TOP_UP:
            steps = [PlanStep(ActionType.WRITE_TOP_UP, "Top up wallet", dict(ctx.entities))]
        else:
            steps = [PlanStep(ActionType.READ_BALANCE, "Check balance or read transactions")]

        return ExecutionPlan(steps=steps, raw_intent=ctx.raw_message)
