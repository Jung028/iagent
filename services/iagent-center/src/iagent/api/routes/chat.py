import structlog
from fastapi import APIRouter, Request

from iagent.api.schemas.chat import ChatRequest, ChatResponse
from iagent.core.intent.models import Intent
from iagent.core.response_builder.builder import build_balance_response, build_error_response

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
    # get instance from classifier, account_client, wallet_client.
    # Classifier is classify, call_llm, 
    # account and wallet client, defined methods are : queryAccountInfo, 
    # wallet : getBalance, getTransactions 
    classifier = http_request.app.state.classifier
    account_client = http_request.app.state.account_client
    business_client = http_request.app.state.business_client

    # Step 1: Classify the user's message.
    # "await" pauses here until classify() finishes (it may call Redis or the LLM).
    # While paused, Python's event loop can handle other incoming requests — this is
    # what makes async I/O efficient vs Java's blocking threads.
    intent_result = await classifier.classify(request.user_id, request.message)

    # Step 2: Route to the correct action based on the classified intent.
    if intent_result.intent == Intent.BALANCE_INQUIRY:
        # get handle 
        from iagent.core.tools.balance import handle
        # query accounts 
        accounts = await handle(
            user_id=request.user_id,
            account_client=account_client,
            business_client=business_client,
            # Pass the request ID so it gets forwarded to Java services for trace correlation.
            # "getattr(obj, "attr", default)" safely reads an attribute, returning the default
            # if it doesn't exist. In Java: Objects.toString(http_request.state.requestId, "")
            request_id=getattr(http_request.state, "request_id", ""),
            user_id_ctx=request.user_id,
        )

        # Step 3: Build and return the ChatResponse with a BalanceCard.
        return build_balance_response(accounts)

    # If the intent wasn't something we handle, return a friendly error card.
    # "return" exits the function immediately — no "else" needed after a return.
    return build_error_response(
        intent=intent_result.intent,
        code="unsupported_intent",
        message="I can currently only help with balance inquiries.",
    )
