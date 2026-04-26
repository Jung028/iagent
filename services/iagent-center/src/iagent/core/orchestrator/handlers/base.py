from abc import ABC, abstractmethod
from typing import Any

from iagent.core.context.models import AgentContext
from iagent.core.orchestrator.result import OrchestratorResult


class ToolHandler(ABC):
    """Abstract base for all intent handlers.

    Each handler receives a fully-populated AgentContext plus the integration
    clients it needs. It returns an OrchestratorResult.

    Naming convention: {IntentName}Handler  e.g. BalanceInquiryHandler
    """

    @abstractmethod
    async def execute(
        self,
        ctx: AgentContext,
        **clients: Any,  # account_client=, business_client=, wallet_client= etc.
    ) -> OrchestratorResult:
        ...



