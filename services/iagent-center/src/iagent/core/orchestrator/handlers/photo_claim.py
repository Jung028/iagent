import structlog
from typing import Any

from iagent.core.context.models import AgentContext
from iagent.core.orchestrator.handlers.base import ToolHandler
from iagent.core.orchestrator.result import OrchestratorResult
from iagent.core.response_builder.builder import build_error_response
from iagent.core.models.intent import Intent

log = structlog.get_logger(__name__)


class PhotoClaimHandler(ToolHandler):
    """Handles Intent.PHOTO_CLAIM.

    User sends a receipt/invoice photo → extract amount, merchant, date → submit claim.
    e.g. user sends an image on WhatsApp: "submit this receipt"
    """

    async def execute(self, ctx: AgentContext, **clients: Any) -> OrchestratorResult:
        # TODO: check ctx.media_attachments — if empty, reply asking user to attach a photo
        # TODO: download image from ctx.media_attachments[0] (pre-signed URL)
        # TODO: call Gemini Vision (or Google Document AI) to extract:
        #   - merchant_name, total_amount, currency, date, line_items
        # TODO: call IBusinessClient.submit_claim(account_id, extracted_data, image_url)
        # TODO: return PhotoClaimCard with extracted details + confirmation (new UI card to add)
        # TODO: if extraction confidence is low → return ConfirmationCard for manual correction

        response = build_error_response(
            intent=Intent.PHOTO_CLAIM,
            code="not_implemented",
            message="Receipt scanning is coming soon.",
        )
        return OrchestratorResult(intent=Intent.PHOTO_CLAIM, ui=response.ui)
