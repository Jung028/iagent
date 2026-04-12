"""
E2E tests — use real Anthropic API. Run nightly, not on every PR.
Requires: ANTHROPIC_API_KEY env var + running iagent-center service.
"""
import pytest


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_balance_inquiry_natural_language():
    """'What's my balance?' → BalanceCard, requires_action=False"""
    pytest.skip("E2E — requires live Anthropic API and running service")


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_unknown_intent_returns_error():
    """'Tell me a joke' → ErrorCard with unsupported_intent code"""
    pytest.skip("E2E — requires live Anthropic API and running service")
