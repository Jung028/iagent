from fastapi import APIRouter, Request

from iagent.api.schemas.reconciliation import ReconciliationSuggestRequest, ReconciliationSuggestion

router = APIRouter(prefix="/api/v1/reconciliation", tags=["reconciliation"])


@router.post("/suggest", response_model=ReconciliationSuggestion)
async def suggest(request: ReconciliationSuggestRequest, http_request: Request) -> ReconciliationSuggestion:
    controller = http_request.app.state.reconciliation_controller
    return await controller.suggest(request)
