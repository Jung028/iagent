import base64

import anthropic
import httpx
import structlog

log = structlog.get_logger(__name__)

_OCR_PROMPT = (
    "Transcribe all visible text in this document exactly as it appears. "
    "Return only the raw text content. Do not summarise or interpret — just transcribe."
)


class OCRService:
    def __init__(self, client: anthropic.AsyncAnthropic) -> None:
        self._client = client

    async def extract_raw_text(self, file_url: str, mime_type: str) -> str:
        async with httpx.AsyncClient(timeout=30.0) as http:
            resp = await http.get(file_url)
            resp.raise_for_status()
            file_bytes = resp.content

        b64 = base64.standard_b64encode(file_bytes).decode()

        if mime_type.startswith("image/"):
            content = [
                {"type": "image", "source": {"type": "base64", "media_type": mime_type, "data": b64}},
                {"type": "text", "text": _OCR_PROMPT},
            ]
        elif mime_type == "application/pdf":
            content = [
                {"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": b64}},
                {"type": "text", "text": _OCR_PROMPT},
            ]
        else:
            # Plain text or unknown — decode and return directly without an LLM call
            return file_bytes.decode("utf-8", errors="replace")

        result = await self._client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=2048,
            messages=[{"role": "user", "content": content}],
        )
        raw_text = result.content[0].text.strip()
        log.info("ocr_complete", chars=len(raw_text), mime_type=mime_type)
        return raw_text
