import structlog

from iagent.api.schemas.extract import DocumentExtractRequest, DocumentExtractResponse, ExtractedFields
from iagent.services.document.llm_extraction_service import LLMExtractionService
from iagent.services.document.ocr_service import OCRService

log = structlog.get_logger(__name__)


class ExtractionController:
    def __init__(self, ocr_service: OCRService, llm_service: LLMExtractionService) -> None:
        self._ocr = ocr_service
        self._llm = llm_service

    async def extract(self, request: DocumentExtractRequest) -> DocumentExtractResponse:
        try:
            raw_text = await self._ocr.extract_raw_text(request.file_url, request.mime_type)
            log.info("ocr_done", source_document_id=request.source_document_id, chars=len(raw_text))

            data      = await self._llm.extract_structured_fields(raw_text)
            extracted = data.get("extracted", {})
            missing   = data.get("missing_fields", [])
            questions = data.get("clarifying_questions", [])

            status = "success" if not missing else "partial"
            log.info("extraction_done", source_document_id=request.source_document_id, status=status)

            return DocumentExtractResponse(
                source_document_id=request.source_document_id,
                status=status,
                extracted=ExtractedFields(**{k: v for k, v in extracted.items() if v is not None}),
                missing_fields=missing,
                clarifying_questions=questions,
                raw_text=raw_text,
            )

        except Exception as exc:
            log.error("extraction_failed", error=str(exc), source_document_id=request.source_document_id)
            return DocumentExtractResponse(
                source_document_id=request.source_document_id,
                status="failed",
                extracted=ExtractedFields(),
                missing_fields=[],
                clarifying_questions=[],
                raw_text=None,
            )
