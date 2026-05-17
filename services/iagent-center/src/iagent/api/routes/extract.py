from fastapi import APIRouter, Request

from iagent.api.schemas.extract import DocumentExtractRequest, DocumentExtractResponse

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])


@router.post("/extract", response_model=DocumentExtractResponse)
async def extract(request: DocumentExtractRequest, http_request: Request) -> DocumentExtractResponse:
    controller = http_request.app.state.extraction_controller
    return await controller.extract(request)
