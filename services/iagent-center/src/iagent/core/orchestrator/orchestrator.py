import structlog

from iagent.api.schemas.chat import ChatResponse
from iagent.core.context.models import AgentContext
from iagent.core.orchestrator.router import IntentRouter
from iagent.core.orchestrator.result import OrchestratorResult

log = structlog.get_logger(__name__)


class Orchestrator:
    """Top-level controller: receives an AgentContext and produces a ChatResponse.

    This is what chat.py delegates to. It owns the dispatch loop.

    Lifecycle (per request):
      1. router.resolve(ctx.intent) → ToolHandler
      2. handler.execute(ctx)       → OrchestratorResult
      3. result.to_chat_response()  → ChatResponse
    """

    """ we create this constructor because we need to use it in the """

    def __init__(self, 
                 router:IntentRouter, 
                 account_client: object, 
                 business_client: object,
                 user_client: object,) -> None :
            self._router=router
            self._account_client=account_client
            self._business_client = business_client
            self._user_client = user_client

    async def run(self, ctx: AgentContext) -> ChatResponse:
        handler = self._router.resolve(ctx.intent)
        result : OrchestratorResult = await handler.execute(
              ctx,
              account_client = self._account_client,
              business_client = self._business_client,
              user_client = self._user_client,

         )

        return result.to_chat_response()

