import structlog

from iagent.api.schemas.reconciliation import ReconciliationSuggestRequest, ReconciliationSuggestion
from iagent.services.document.reconciliation_service import ReconciliationService

log = structlog.get_logger(__name__)


class ReconciliationController:
    def __init__(self, reconciliation_service: ReconciliationService) -> None:
        self._service = reconciliation_service

    async def suggest(self, request: ReconciliationSuggestRequest) -> ReconciliationSuggestion:
        try:
            return await self._service.suggest(request)
        except Exception as exc:
            log.error("reconciliation_suggest_failed", error=str(exc))
            # fall back to the first candidate so Java always gets a response to decide on
            first = request.candidate_bank_transactions[0]
            return ReconciliationSuggestion(
                suggested_bank_transaction_id=first.bank_transaction_id,
                confidence_score=0.50,
                reason=f"Agent error ({exc}); defaulting to first candidate.",
            )
