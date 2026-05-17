import structlog

from iagent.api.schemas.extract import DocumentExtractRequest, DocumentExtractResponse, ExtractedFields
from iagent.services.document.llm_extraction_service import LLMExtractionService
from iagent.services.document.ocr_service import OCRService

log = structlog.get_logger(__name__)


class DocumentExtractionService:
    def __init__(self, ocr: OCRService, llm: LLMExtractionService) -> None:
        self._ocr = ocr
        self._llm = llm

    async def extract_document(self, request: DocumentExtractRequest) -> DocumentExtractResponse:
        log.info("extraction_started", source_document_id=request.source_document_id)

        raw_text = await self._ocr.extract_raw_text(request.file_url, request.mime_type)

        data = await self._llm.extract_structured_fields(raw_text)
        extracted = data.get("extracted", {})
        missing = data.get("missing_fields", [])
        questions = data.get("clarifying_questions", [])

        status = "success" if not missing else "partial"
        log.info("extraction_complete", source_document_id=request.source_document_id, status=status)

        return DocumentExtractResponse(
            source_document_id=request.source_document_id,
            status=status,
            extracted=ExtractedFields(**{k: v for k, v in extracted.items() if v is not None}),
            missing_fields=missing,
            clarifying_questions=questions,
            raw_text=raw_text,
        )
