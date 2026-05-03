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


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest, http_request: Request) -> ChatResponse:

    # RAG 1 : get context from RAG, including profile, entities and recent messages. 
    rag_service = getattr(http_request.app.state, "rag_service", None)
    memory_context: dict = {}
    if rag_service:
        # get context from RAG, includes profile, entities, recent messages.
        memory_context = await rag_service.get_context(
            user_id=request.user_id,
            message=request.message,
            thread_id=getattr(request, "thread_id", None),
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

    response = await http_request.app.state.orchestrator.run(ctx)

    # RAG 2 : store the interaction, message, intent, entities and response for future retrieval
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
