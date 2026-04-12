"""
Integration tests for POST /chat.
Requires: real Postgres + Redis (via testcontainers), WireMock for Java services.
"""
import pytest
from httpx import AsyncClient

# TODO: wire up testcontainers fixtures and app client


@pytest.mark.integration
@pytest.mark.asyncio
async def test_balance_inquiry_returns_balance_card():
    pytest.skip("Requires testcontainers setup")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_money_transfer_returns_confirmation_card():
    pytest.skip("Requires testcontainers setup")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_unknown_intent_returns_error_card():
    pytest.skip("Requires testcontainers setup")
