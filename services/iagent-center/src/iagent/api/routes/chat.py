from iagent.core.context.service_context import ServiceContext
from iagent.core.intent.intent_contract_requirements import INTENT_REQUIREMENTS
from iagent.core.models.validation import ValidationStatus
from iagent.core.response_builder.builder import build_error_response
from iagent.core.validator.intent_validator import IntentValidator
import structlog
from fastapi import APIRouter, Request

from iagent.api.schemas.chat import ChatRequest, ChatResponse
from iagent.core.context.builder import ContextBuilder

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


def _extract_assistant_text(response: ChatResponse) -> str:
    """Extract a plain-text summary from the UI card to store as assistant history.

    This is what Claude will see as its own previous reply in the next turn.
    """
    ui = response.ui
    if ui is None:
        return ""

    card_type = getattr(ui, "type", "")

    if card_type == "text_response":
        return getattr(ui, "message", "")

    if card_type == "structured_response":
        # Include summary + section titles so Claude knows what it said
        summary = getattr(ui, "summary", "")
        sections = getattr(ui, "sections", []) or []
        if not sections:
            return summary
        section_titles = ", ".join(
            s.title for s in sections if getattr(s, "title", None)
        )
        return f"{summary} [{section_titles}]" if section_titles else summary

    if card_type == "balance_card":
        accounts = getattr(ui, "accounts", []) or []
        if accounts:
            a = accounts[0]
            return f"Balance: {a.currency} {a.balance:.2f}"
        return "Balance retrieved."

    if card_type == "transaction_details_card":
        txn = getattr(ui, "transaction_details", None)
        if txn:
            return f"Transaction {txn.txn_id}: {txn.currency} {txn.amount:.2f}"
        return "Transaction details retrieved."

    if card_type == "transaction_history_card":
        history = getattr(ui, "transaction_history", []) or []
        return f"Returned {len(history)} transaction(s)."

    if card_type == "transaction_analysis_card":
        analysis = getattr(ui, "analysis", None)
        if analysis:
            return getattr(analysis, "summary", "Analysis complete.")
        return "Analysis complete."

    if card_type == "error_card":
        return getattr(ui, "message", "An error occurred.")

    return ""


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest, http_request: Request) -> ChatResponse:

    # RAG 1: get context from RAG — profile, entities, recent messages
    rag_service = getattr(http_request.app.state, "rag_service", None)
    memory_context: dict = {}
    if rag_service:
        service_context = ServiceContext(
            user_id=request.user_id,
            phone_no=request.phone_no,
            request_id=getattr(http_request.state, "request_id", ""),
            session_id=request.session_id or "",
            auth_token=http_request.headers.get("Authorization"),
        )
        memory_context = await rag_service.get_context(
            user_id=request.user_id,
            message=request.message,
            thread_id=getattr(request, "thread_id", None),
            service_ctx=service_context,
        )

    intent_result = await http_request.app.state.classifier.classify(
        request.user_id, request.message
    )

    ctx = await ContextBuilder.from_request(
        request=request,
        intent_result=intent_result,
        request_id=getattr(http_request.state, "request_id", ""),
        session_store=getattr(http_request.app.state, "session_store", None),
        profile_loader=getattr(http_request.app.state, "profile_loader", None),
        auth_token=http_request.headers.get("Authorization"),
        memory_context=memory_context,
    )

    validate_result = await IntentValidator.validate(
        intent_result.intent.value,
        intent_result.entities
    )

    if validate_result.status == ValidationStatus.INSUFFICIENT_CONTEXT:
        return build_error_response(
            intent=ctx.intent,
            code="missing_required_fields",
            message=validate_result.question or "I need more information.",
        )

    ctx.entities.update(validate_result.cleaned_entities)

    if request.confirmed:
        ctx.entities["confirmed"] = True
    if request.pin:
        ctx.entities["pin"] = request.pin

    response = await http_request.app.state.orchestrator.run(ctx)

    # Save conversation turn to session history so future requests have memory
    session_store = getattr(http_request.app.state, "session_store", None)
    if session_store and ctx.session_id:
        await session_store.append(ctx.session_id, {
            "role":    "user",
            "content": request.message,
            "intent":  intent_result.intent.value,
        })
        assistant_text = _extract_assistant_text(response)
        if assistant_text:
            await session_store.append(ctx.session_id, {
                "role":    "assistant",
                "content": assistant_text,
            })

    # RAG 2: store interaction for future semantic retrieval
    if rag_service:
        await rag_service.store(
            user_id=request.user_id,
            thread_id=memory_context.get("thread_id", ""),
            message=request.message,
            intents=intent_result,
            entities=ctx.entities,
            result=response,
        )

    return response
