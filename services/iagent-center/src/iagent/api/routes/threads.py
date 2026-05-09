import structlog
from fastapi import APIRouter, HTTPException, Query, Request

from iagent.api.schemas.threads import ThreadDetailResponse, ThreadListResponse, ThreadSummary, InteractionItem

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/threads", tags=["threads"])


@router.get("", response_model=ThreadListResponse)
async def list_threads(
    user_id: str = Query(..., alias="userId"),
    http_request: Request = None,
) -> ThreadListResponse:
    """
    SELECT * FROM thread WHERE user_id = ? ORDER BY updated_at DESC

    Returns all threads for a user, most recently active first.
    Called on page load / chatbot open so the sidebar can populate.
    """
    rag_service = getattr(http_request.app.state, "rag_service", None)
    if not rag_service:
        return ThreadListResponse(threads=[])

    raw = await rag_service.list_threads(user_id)
    return ThreadListResponse(
        threads=[ThreadSummary(**t) for t in raw]
    )


@router.get("/{thread_id}", response_model=ThreadDetailResponse)
async def get_thread(thread_id: str, http_request: Request) -> ThreadDetailResponse:
    """
    SELECT * FROM interaction WHERE thread_id = ? ORDER BY created_at ASC

    Returns the full ordered interaction history for a thread (oldest at top,
    newest at bottom) plus the thread's structured summary so the model can
    continue where it left off.
    """
    rag_service = getattr(http_request.app.state, "rag_service", None)
    if not rag_service:
        raise HTTPException(status_code=503, detail="RAG service unavailable")

    data = await rag_service.get_thread_detail(thread_id)
    return ThreadDetailResponse(
        thread_id=data["thread_id"],
        summary=data["summary"],
        interactions=[InteractionItem(**i) for i in data["interactions"]],
    )
