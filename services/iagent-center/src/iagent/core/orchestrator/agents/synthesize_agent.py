from datetime import date

import anthropic
import structlog

from iagent.core.context.models import AgentContext
from iagent.core.orchestrator.agents.plan import ExecutionPlan
from iagent.core.orchestrator.result import OrchestratorResult

log = structlog.get_logger(__name__)

MODEL = "claude-haiku-4-5"

SYNTHESIZE_TOOL = {
    "name": "synthesize_response",
    "description": (
        "Compose the final user-facing response based on the results of all executed steps. "
        "Call this once and only once — it is your final output."
    ),
    "input_schema": {
        "type": "object",
        "required": ["summary"],
        "properties": {
            "summary": {
                "type": "string",
                "description": (
                    "Friendly, conversational sentence(s) addressing the user by first name. "
                    "Combine all step results into one coherent reply."
                ),
            },
            "sections": {
                "type": "array",
                "description": "Optional breakdown sections. Empty [] for simple one-fact answers.",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "items": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "label": {"type": "string"},
                                    "value": {"type": "string"},
                                    "text": {"type": "string"},
                                },
                            },
                        },
                    },
                },
            },
        },
    },
}

SYSTEM_TEMPLATE = """\
You are the SynthesizeAgent Agent (Synthesis) for iAgent, an eWallet assistant for {name}.
Today is {today}.

Your job: turn raw execution results into a single friendly, human-readable reply.

RULES:
- Address the user by first name.
- Be concise — combine all results into one or two sentences when possible.
- Use sections only when there is genuinely structured data to display (e.g. transaction list).
- Format currency amounts as RM X.XX (e.g. RM 50.00).
- Format dates as D Mon YYYY at H:MM AM/PM.
- No markdown, no emojis, no ** or # symbols.
- If a greeting step is in the plan, open with a warm greeting by name.
- If a step resulted in an error, acknowledge it honestly.
- Always call synthesize_response. Never reply in plain text.
"""


class SynthesizeAgent:
    """Synthesis agent — turns raw execution results into a friendly chat response."""

    def __init__(self, client: anthropic.AsyncAnthropic) -> None:
        self._client = client

    async def synthesize(
        self,
        ctx: AgentContext,
        plan: ExecutionPlan,
        results: list[dict],
    ) -> OrchestratorResult:
        system = self._build_system(ctx)
        user_content = self._build_prompt(ctx, plan, results)

        try:
            response = await self._client.messages.create(
                model=MODEL,
                max_tokens=1024,
                system=system,
                tools=[SYNTHESIZE_TOOL],
                tool_choice={"type": "any"},
                messages=[{"role": "user", "content": user_content}],
            )

            for block in response.content:
                if block.type == "tool_use" and block.name == "synthesize_response":
                    log.info("synthesize_agent_done")
                    return OrchestratorResult(
                        intent=ctx.intent,
                        ui={
                            "type": "structured_response",
                            "summary": block.input.get("summary", ""),
                            "sections": block.input.get("sections") or [],
                        },
                        requires_action=False,
                    )
        except Exception as exc:
            log.warning("synthesize_agent_failed", error=str(exc))

        return OrchestratorResult(
            intent=ctx.intent,
            ui={"type": "text_response", "message": "Done. How else can I help?"},
            requires_action=False,
        )

    def _build_system(self, ctx: AgentContext) -> str:
        name = (ctx.user_profile or {}).get("name", "there")
        system = SYSTEM_TEMPLATE.format(name=name, today=date.today().isoformat())
        if ctx.thread_summary:
            system += f"\n\nPREVIOUS SESSION SUMMARY:\n{ctx.thread_summary}\n"
        return system

    def _build_prompt(
        self,
        ctx: AgentContext,
        plan: ExecutionPlan,
        results: list[dict],
    ) -> str:
        lines = [
            f'User\'s original request: "{ctx.raw_message}"',
            "",
            "Execution results:",
        ]
        for i, (step, result) in enumerate(zip(plan.steps, results, strict=False), 1):
            lines.append(f"  Step {i} ({step.action_type} — {step.description}): {result}")
        return "\n".join(lines)
