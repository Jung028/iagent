import httpx
import pytest
from iagent.integrations.base import BaseServiceClient
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_base_service_client_forwards_auth_token(mocker):
    client = BaseServiceClient(base_url="http://test", service_name="test", token_provider=None)
    
    # Mock the internal httpx.AsyncClient.request method
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.is_success = True
    
    mocker.patch.object(client._http, "request", new_callable=AsyncMock, return_value=mock_response)
    
    await client._request(
        "POST",
        "/api",
        auth_token="Bearer test-token",
        request_id="req-123"
    )
    
    client._http.request.assert_called_once()
    args, kwargs = client._http.request.call_args
    headers = kwargs["headers"]
    assert headers["Authorization"] == "Bearer test-token"
    assert headers["X-Request-ID"] == "req-123"

@pytest.mark.asyncio
async def test_base_service_client_uses_token_provider_if_no_auth_token(mocker):
    class MockTokenProvider:
        async def get_token(self):
            return "system-token"
            
    client = BaseServiceClient(base_url="http://test", service_name="test", token_provider=MockTokenProvider())
    
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.is_success = True
    mocker.patch.object(client._http, "request", new_callable=AsyncMock, return_value=mock_response)
    
    await client._request(
        "POST",
        "/api",
        request_id="req-123"
    )
    
    client._http.request.assert_called_once()
    args, kwargs = client._http.request.call_args
    headers = kwargs["headers"]
    assert headers["Authorization"] == "Bearer system-token"

@pytest.mark.asyncio
async def test_base_service_client_auth_token_overrides_token_provider(mocker):
    class MockTokenProvider:
        async def get_token(self):
            return "system-token"
            
    client = BaseServiceClient(base_url="http://test", service_name="test", token_provider=MockTokenProvider())
    
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.is_success = True
    mocker.patch.object(client._http, "request", new_callable=AsyncMock, return_value=mock_response)
    
    await client._request(
        "POST",
        "/api",
        auth_token="Bearer user-token",
        request_id="req-123"
    )
    
    client._http.request.assert_called_once()
    args, kwargs = client._http.request.call_args
    headers = kwargs["headers"]
    assert headers["Authorization"] == "Bearer user-token"
