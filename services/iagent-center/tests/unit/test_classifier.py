import json
import pytest
from unittest.mock import AsyncMock, MagicMock

from iagent.core.intent.classifier import IntentClassifier
from iagent.core.intent.models import Intent, IntentResult


def _make_gemini_response(intent: str, confidence: float = 0.95):
    """Helper to mock a Gemini tool-call response."""
    fc = MagicMock()
    fc.name = "extract_financial_intent"
    fc.args = {"intent": intent, "confidence": confidence}

    part = MagicMock()
    part.function_call = fc

    content = MagicMock()
    content.parts = [part]

    candidate = MagicMock()
    candidate.content = content

    response = MagicMock()
    response.candidates = [candidate]
    return response


@pytest.mark.asyncio
async def test_balance_inquiry_classified(mock_gemini_client, mock_redis):
    mock_gemini_client.aio.models.generate_content = AsyncMock(
        return_value=_make_gemini_response("balance_inquiry")
    )
    classifier = IntentClassifier(mock_gemini_client, mock_redis)
    result = await classifier.classify("user-1", "What's my balance?")
    assert result.intent == Intent.BALANCE_INQUIRY
    assert result.confidence == 0.95


@pytest.mark.asyncio
async def test_unknown_on_api_error(mock_gemini_client, mock_redis):
    # Simulate a 429 or network error
    mock_gemini_client.aio.models.generate_content = AsyncMock(
        side_effect=RuntimeError("429 RESOURCE_EXHAUSTED")
    )
    classifier = IntentClassifier(mock_gemini_client, mock_redis)
    
    # First call: hits API, gets UNKNOWN, should cache it
    result1 = await classifier.classify("user-1", "bad message")
    assert result1.intent == Intent.UNKNOWN
    assert mock_gemini_client.aio.models.generate_content.call_count == 1
    
    # Verify it was cached (mock_redis.setex should have been called)
    assert mock_redis.setex.called
    
    # Mock redis.get to return the cached UNKNOWN result for the second call
    mock_redis.get = AsyncMock(
        return_value=json.dumps(
            {"intent": "unknown", "confidence": 0.0, "entities": {}}
        ).encode()
    )
    
    # Second call: should HIT CACHE (even if UNKNOWN) and NOT call API
    result2 = await classifier.classify("user-1", "bad message")
    assert result2.intent == Intent.UNKNOWN
    assert result2.cache_hit is True
    assert mock_gemini_client.aio.models.generate_content.call_count == 1  # Still 1


@pytest.mark.asyncio
async def test_cache_hit_skips_api(mock_gemini_client, mock_redis):
    mock_redis.get = AsyncMock(
        return_value=json.dumps(
            {"intent": "balance_inquiry", "confidence": 0.9, "entities": {}}
        ).encode()
    )
    classifier = IntentClassifier(mock_gemini_client, mock_redis)
    result = await classifier.classify("user-1", "What's my balance?")
    assert result.intent == Intent.BALANCE_INQUIRY
    assert result.cache_hit is True
    mock_gemini_client.aio.models.generate_content.assert_not_called()
