from iagent.core.intent.intent_contract_requirements import INTENT_REQUIREMENTS
from iagent.core.models.validation import ValidationStatus
from iagent.core.response_builder.builder import build_error_response
from iagent.core.validator.intent_validator import IntentValidator
import structlog
from fastapi import APIRouter, Request

from iagent.api.schemas.chat import ChatRequest, ChatResponse
from iagent.core.context.builder import ContextBuilder

# Module-level logger — used to emit structured JSON log lines from this file.
log = structlog.get_logger(__name__)

# APIRouter is like a Spring @RestController — it groups related route handlers together.
# "prefix="/chat"" means all routes defined on this router start with /chat.
# "tags=["chat"]" is only for the auto-generated API documentation at /docs.
router = APIRouter(prefix="/chat", tags=["chat"])


# "@router.post("")" is a DECORATOR that registers the function below as the handler
# for "POST /chat" (empty string = no extra path segment after the prefix "/chat").
# In Java Spring: @PostMapping("/chat")
#
# "response_model=ChatResponse" tells FastAPI the shape of what this function returns.
# FastAPI uses it to: (1) validate the response before sending, and (2) generate API docs.
@router.post("", response_model=ChatResponse)
@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest, http_request: Request) -> ChatResponse:

    # ── EXISTING ──────────────────────────────────────────
    intent_result = await http_request.app.state.classifier.classify(
        request.user_id, request.message
    )

    # ── RAG INJECTION POINT 1 ─────────────────────────────
    # inject before ContextBuilder so context is enriched
    rag = http_request.app.state.rag_service
    memory_context = await rag.get_context(
        user_id=request.user_id,
        message=request.message
    )
    # memory_context = { profile, contacts, entities, history }

    # ── EXISTING (pass memory_context in) ─────────────────
    ctx = await ContextBuilder.from_request(
        request=request,
        intent_result=intent_result,
        request_id=getattr(http_request.state, "request_id", ""),
        session_store=getattr(http_request.app.state, "session_store", None),
        profile_loader=getattr(http_request.app.state, "profile_loader", None),
        auth_token=http_request.headers.get("Authorization"),
        memory_context=memory_context,   # ← new param added
    )

    # ── EXISTING ──────────────────────────────────────────
    validate_result = await IntentValidator.validate(
        intent_result.intent.value, 
        intent_result.entities
    )

    if validate_result.status == ValidationStatus.UNKNOWN_INTENT:
        return build_error_response(
            intent=ctx.intent,
            code="unsupported_intent",
            message="I'm not sure what you're asking.",
        )

    if validate_result.status == ValidationStatus.INSUFFICIENT_CONTEXT:
        return build_error_response(
            intent=ctx.intent,
            code="missing_required_fields",
            message=validate_result.question or "I need more information.",
        )

    ctx.entities.update(validate_result.cleaned_entities)

    # ── EXISTING ──────────────────────────────────────────
    response = await http_request.app.state.orchestrator.run(ctx)

    # ── RAG INJECTION POINT 2 ─────────────────────────────
    # store after orchestrator finishes so memory is updated
    await rag.store(
        user_id=request.user_id,
        intents=intent_result,
        entities=ctx.entities,
        result=response
    )

    return response