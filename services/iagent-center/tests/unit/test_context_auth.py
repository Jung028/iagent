import pytest
from iagent.core.context.builder import ContextBuilder
from iagent.api.schemas.chat import ChatRequest
from iagent.core.models.intent import IntentResult
from iagent.core.models.intent import Intent

@pytest.mark.asyncio
async def test_context_builder_captures_auth_token():
    request = ChatRequest(
        user_id="user-123",
        message="hello",
        phone_no="123456789"
    )
    intent_result = IntentResult(
        intent=Intent.BALANCE_INQUIRY,
        confidence=0.9,
        entities={}
    )
    
    ctx = await ContextBuilder.from_request(
        request=request,
        intent_result=intent_result,
        request_id="req-123",
        auth_token="Bearer my-token"
    )
    
    assert ctx.auth_token == "Bearer my-token"
    
    # Test to_service_ctx
    service_ctx = ctx.to_service_ctx()
    assert service_ctx["auth_token"] == "Bearer my-token"
    assert service_ctx["request_id"] == "req-123"

@pytest.mark.asyncio
async def test_context_builder_no_auth_token():
    request = ChatRequest(
        user_id="user-123",
        message="hello",
        phone_no="123456789"
    )
    intent_result = IntentResult(
        intent=Intent.BALANCE_INQUIRY,
        confidence=0.9,
        entities={}
    )
    
    ctx = await ContextBuilder.from_request(
        request=request,
        intent_result=intent_result,
        request_id="req-123"
    )
    
    assert ctx.auth_token is None
    
    # Test to_service_ctx
    service_ctx = ctx.to_service_ctx()
    assert "auth_token" not in service_ctx
