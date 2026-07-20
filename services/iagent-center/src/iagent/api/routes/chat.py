import base64
import json

from iagent.core.context.service_context import ServiceContext
from iagent.core.intent.intent_contract_requirements import INTENT_REQUIREMENTS
from iagent.core.models.validation import ValidationStatus
from iagent.core.response_builder.builder import build_error_response
from iagent.core.validator.intent_validator import IntentValidator
from iagent.api.schemas.ui_cards import BookkeepingCard, BookkeepingEntry, TextResponseCard, ErrorCard
import structlog
from fastapi import APIRouter, File, Form, Request, UploadFile

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

    response = await http_request.app.state.orchestrator.run(ctx)

    assistant_text = _extract_assistant_text(response)

    # Save conversation turn to session history so future requests have memory
    session_store = getattr(http_request.app.state, "session_store", None)
    if session_store and ctx.session_id:
        await session_store.append(ctx.session_id, {
            "role":    "user",
            "content": request.message,
            "intent":  intent_result.intent.value,
        })
        if assistant_text:
            await session_store.append(ctx.session_id, {
                "role":    "assistant",
                "content": assistant_text,
            })

    # RAG 2: store interaction for future semantic retrieval
    if rag_service:
        stored_thread_id = await rag_service.store(
            user_id=request.user_id,
            thread_id=memory_context.get("thread_id", ""),
            message=request.message,
            intents=intent_result,
            entities=ctx.entities,
            result=response,
            assistant_text=assistant_text,
        )
        if stored_thread_id:
            response.thread_id = stored_thread_id

    return response


_BOOKKEEPING_SYSTEM = (
    "You are a bookkeeping assistant. Analyse the receipt or document and extract:\n"
    "- vendor: merchant/business name\n"
    "- date: transaction date in YYYY-MM-DD format\n"
    "- amount: total amount as a decimal number\n"
    "- currency: 3-letter currency code (default MYR if not visible)\n"
    "- category: exactly one of [GROCERIES, FOOD_DINING, TRANSPORT, FUEL, SHOPPING, "
    "ENTERTAINMENT, UTILITIES, RENT, HEALTHCARE, EDUCATION, TRANSFER, TOP_UP, OTHER]\n"
    "- description: brief description, max 60 chars\n\n"
    "Rules: only fill fields you are CERTAIN about. Set uncertain/missing fields to null "
    "and list them in missing_fields with a clarifying question for each.\n\n"
    "Respond ONLY with valid JSON (no markdown):\n"
    '{"extracted":{"vendor":null,"date":null,"amount":null,"currency":null,'
    '"category":null,"description":null},"missing_fields":[],"clarifying_questions":[]}'
)

_QUESTION_SYSTEM = (
    "You are a helpful assistant. Answer the user's question about the attached document "
    "or image concisely and accurately. If the answer is not visible in the document, say so."
)


def _build_file_content(file_bytes: bytes, media_type: str, prompt: str) -> list:
    b64 = base64.standard_b64encode(file_bytes).decode()
    if media_type.startswith("image/"):
        return [
            {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64}},
            {"type": "text", "text": prompt},
        ]
    if media_type == "application/pdf":
        return [
            {"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": b64}},
            {"type": "text", "text": prompt},
        ]
    # Fallback: treat as plain text
    try:
        text = file_bytes.decode("utf-8", errors="replace")
    except Exception:
        text = "(binary file — cannot display)"
    return [{"type": "text", "text": f"Document content:\n{text}\n\n{prompt}"}]


@router.post("/upload", response_model=ChatResponse)
async def chat_upload(
    user_id: str = Form(...),
    action: str = Form(...),          # "bookkeeping" | "question"
    message: str = Form(default=""),  # user's question (for action=question)
    session_id: str = Form(default=""),
    file: UploadFile = File(...),
    http_request: Request = None,
) -> ChatResponse:
    anthropic_client = http_request.app.state.anthropic_client
    file_bytes  = await file.read()
    media_type  = file.content_type or "application/octet-stream"

    try:
        if action == "bookkeeping":
            content = _build_file_content(
                file_bytes, media_type,
                "Extract all bookkeeping fields from this receipt or document.",
            )
            resp = await anthropic_client.messages.create(
                model="claude-haiku-4-5",
                max_tokens=1024,
                system=_BOOKKEEPING_SYSTEM,
                messages=[{"role": "user", "content": content}],
            )
            raw = resp.content[0].text.strip()
            # Strip markdown fences if present
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            data       = json.loads(raw)
            extracted  = data.get("extracted", {})
            missing    = data.get("missing_fields", [])
            questions  = data.get("clarifying_questions", [])

            if missing:
                msg = (
                    "I extracted some information but need a few clarifications before adding this entry:\n"
                    + "\n".join(f"• {q}" for q in questions)
                )
            else:
                msg = "I extracted the following bookkeeping entry. Please confirm to add it."

            return ChatResponse(
                intent="bookkeeping_entry",
                ui=BookkeepingCard(
                    entry=BookkeepingEntry(**{k: v for k, v in extracted.items() if v is not None}),
                    missing_fields=missing,
                    clarifying_questions=questions,
                    message=msg,
                ),
            )

        else:  # action == "question"
            prompt  = message.strip() or "What is this document about?"
            content = _build_file_content(file_bytes, media_type, prompt)
            resp = await anthropic_client.messages.create(
                model="claude-haiku-4-5",
                max_tokens=1024,
                system=_QUESTION_SYSTEM,
                messages=[{"role": "user", "content": content}],
            )
            answer = resp.content[0].text.strip()
            return ChatResponse(
                intent="document_question",
                ui=TextResponseCard(message=answer),
            )

    except Exception as exc:
        log.error("chat_upload_error", error=str(exc))
        return ChatResponse(
            intent="error",
            ui=ErrorCard(
                code="upload_error",
                message="Sorry, I couldn't process the file. Please try again.",
                recoverable=True,
            ),
        )
