import json
import pytest
from unittest.mock import AsyncMock, MagicMock

from iagent.core.intent.classifier import IntentClassifier
from iagent.core.intent.models import Intent


def _make_tool_response(intent: str, confidence: float = 0.95):
    block = MagicMock()
    block.type = "tool_use"
    block.name = "extract_financial_intent"
    block.input = {"intent": intent, "confidence": confidence}
    response = MagicMock()
    response.content = [block]
    return response


@pytest.mark.asyncio
async def test_balance_inquiry_classified(mock_anthropic_client, mock_redis):
    mock_anthropic_client.messages.create = AsyncMock(
        return_value=_make_tool_response("balance_inquiry")
    )
    classifier = IntentClassifier(mock_anthropic_client, mock_redis)
    result = await classifier.classify("user-1", "What's my balance?")
    assert result.intent == Intent.BALANCE_INQUIRY
    assert result.confidence == 0.95


@pytest.mark.asyncio
async def test_unknown_on_api_error(mock_anthropic_client, mock_redis):
    mock_anthropic_client.messages.create = AsyncMock(side_effect=RuntimeError("API down"))
    classifier = IntentClassifier(mock_anthropic_client, mock_redis)
    result = await classifier.classify("user-1", "What's my balance?")
    assert result.intent == Intent.UNKNOWN


@pytest.mark.asyncio
async def test_cache_hit_skips_api(mock_anthropic_client, mock_redis):
    mock_redis.get = AsyncMock(
        return_value=json.dumps(
            {"intent": "balance_inquiry", "confidence": 0.9, "entities": {}}
        ).encode()
    )
    classifier = IntentClassifier(mock_anthropic_client, mock_redis)
    result = await classifier.classify("user-1", "What's my balance?")
    assert result.intent == Intent.BALANCE_INQUIRY
    assert result.cache_hit is True
    mock_anthropic_client.messages.create.assert_not_called()
