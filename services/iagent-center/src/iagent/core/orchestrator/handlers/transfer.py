from iagent.core.context.models import AgentContext
from iagent.core.orchestrator.handlers.base import ToolHandler
from iagent.core.orchestrator.result import OrchestratorResult


class TransferHandler(ToolHandler):

    async def execute(self, ctx: AgentContext, **clients) -> OrchestratorResult:
        # Step 1 — resolve payee name to account number via contact lookup
        # Step 2 — call transferInit
        # Step 3 — return ConfirmationCard with transferToken stored in session
        #           so the next turn can call transferConfirm
        ...

    async def confirm(self, ctx: AgentContext, **clients) -> OrchestratorResult:
        # Called on the NEXT turn when user submits PIN
        # Reads transferToken from session
        # Calls transferConfirm
        # Returns ResultCard
        ...