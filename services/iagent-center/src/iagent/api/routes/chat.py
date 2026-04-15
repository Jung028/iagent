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
async def chat(request: ChatRequest, http_request: Request) -> ChatResponse:
    """Handle POST /chat — the main entry point for all user messages.

    FastAPI automatically deserialises the JSON request body into a ChatRequest object
    and passes it as the "request" parameter. This is like @RequestBody in Spring MVC.

    "http_request: Request" gives us access to the raw HTTP request (headers, app.state, etc.).
    FastAPI injects this automatically when it sees "Request" in the parameter list.
    In Java Spring this is like adding HttpServletRequest to the method parameters.
    """

    # Step 1: Classify the user's message.
    # "await" pauses here until classify() finishes (it may call Redis or the LLM).
    # While paused, Python's event loop can handle other incoming requests — this is
    # what makes async I/O efficient vs Java's blocking threads.
    intent_result = await http_request.app.state.classifier.classify(
        request.user_id, request.message
    )

    # Step 2: Build the full request context.
    # ContextBuilder.from_request is a static method (not a constructor), so we call it
    # on the class directly — not with ContextBuilder(...).
    # It is "async" (needs "await") because it may call Redis and iAccount internally.
    # request_id is a plain string extracted from request.state — not the request object itself.
    ctx = await ContextBuilder.from_request(
        request=request,
        intent_result=intent_result,
        request_id=getattr(http_request.state, "request_id", ""),
        session_store=getattr(http_request.app.state, "session_store", None),
        profile_loader=getattr(http_request.app.state, "profile_loader", None),
    )

    # Step 3: Delegate to the orchestrator — it picks the right handler and returns the response.
    # ctx must be passed in — without it the orchestrator has nothing to dispatch on.
    return await http_request.app.state.orchestrator.run(ctx)
