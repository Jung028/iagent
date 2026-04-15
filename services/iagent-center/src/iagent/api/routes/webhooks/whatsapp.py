"""WhatsApp webhook endpoint.

Two routes:
  GET  /webhooks/whatsapp  — Meta's one-time hub challenge verification
  POST /webhooks/whatsapp  — Incoming messages from users
"""
import structlog
from fastapi import APIRouter, Request, Response, HTTPException
from fastapi.responses import PlainTextResponse

from iagent.integrations.platforms.whatsapp.adapter import WhatsAppAdapter
from iagent.core.context.builder import ContextBuilder
from iagent.api.schemas.chat import ChatRequest

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/webhooks/whatsapp", tags=["webhooks"])


@router.get("")
async def verify_webhook(
    http_request: Request,
) -> PlainTextResponse:
    """Handle Meta's one-time webhook verification (hub challenge).

    Meta sends: ?hub.mode=subscribe&hub.verify_token=...&hub.challenge=...
    We must respond with the challenge string to confirm endpoint ownership.
    """
    params = http_request.query_params
    mode = params.get("hub.mode", "")
    token = params.get("hub.verify_token", "")
    challenge = params.get("hub.challenge", "")

    verifier = http_request.app.state.whatsapp_adapter._verifier
    result = verifier.verify_hub_challenge(mode, token, challenge)
    if result is None:
        raise HTTPException(status_code=403, detail="Verification failed")

    return PlainTextResponse(result)


@router.post("")
async def receive_message(http_request: Request) -> Response:
    """Receive and process an incoming WhatsApp message.

    Meta expects a 200 response quickly — we process asynchronously.
    """
    # TODO: verify X-Hub-Signature-256 header before processing
    # raw_body = await http_request.body()
    # sig = http_request.headers.get("X-Hub-Signature-256", "")
    # if not adapter._verifier.verify_signature(raw_body, sig):
    #     raise HTTPException(status_code=401, detail="Invalid signature")

    payload = await http_request.json()
    adapter: WhatsAppAdapter = http_request.app.state.whatsapp_adapter

    messages = await adapter.parse_webhook(payload)
    if not messages:
        # Delivery receipts, status updates — acknowledge and ignore
        return Response(status_code=200)

    orchestrator = http_request.app.state.orchestrator
    classifier = http_request.app.state.classifier

    for inbound in messages:
        try:
            # Reuse the same classification + context pipeline as POST /chat
            intent_result = await classifier.classify(inbound.user_id, inbound.message)

            ctx = await ContextBuilder.from_request(
                request=ChatRequest(user_id=inbound.user_id, message=inbound.message),
                intent_result=intent_result,
                request_id=getattr(http_request.state, "request_id", ""),
                session_store=getattr(http_request.app.state, "session_store", None),
                profile_loader=getattr(http_request.app.state, "profile_loader", None),
            )
            # TODO: set ctx.platform = inbound.platform once AgentContext.platform is added
            # TODO: set ctx.media_attachments = inbound.media_urls

            response = await orchestrator.run(ctx)
            await adapter.send_response(inbound, response)

        except Exception as exc:
            log.exception("whatsapp_message_processing_failed", error=str(exc))
            # TODO: send a generic error message back to the user via adapter.send_response()

    # Always return 200 to Meta — retries happen if we return non-200
    return Response(status_code=200)
