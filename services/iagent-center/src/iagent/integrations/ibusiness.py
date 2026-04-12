from typing import Any

from iagent.integrations.base import BaseServiceClient


class IBusinessClient(BaseServiceClient):
    """HTTP client for the iBusiness Java service.

    iBusiness is the source of financial truth for balance and transaction data.
    All balance queries and transfer operations go through this service.

    Corresponds to BusinessBasicController on the Java side.
    Inherits all retry, circuit breaker, and auth logic from BaseServiceClient.
    """

    async def query_balance(self, account_id: str, **ctx: str) -> dict[str, Any]:
        """Fetch the current balance for an account.

        Calls POST /business/basic/queryBalance.json on the business service.
        The response is wrapped in BusinessBizResult<BusinessBalanceResult>; we extract .data.

        Returns a dict like:
        {"currency": "USD", "available": 250.00, "pending": 0.0}

        "available" = funds the user can spend right now.
        "pending"   = funds reserved by in-progress transactions (not yet settled).
        """

        # POST with a JSON body — matches @PostMapping + @RequestBody on the Java side.
        # In Java: BusinessBalanceRequest request = new BusinessBalanceRequest(accountId)
        response = await self._request(
            "POST",
            "/business/basic/queryBalance.json",
            json={"accountId": account_id},
            **ctx,
        )

        response.raise_for_status()

        # The Java service wraps the payload in BusinessBizResult<BusinessBalanceResult>.
        # The actual balance data lives in the "data" field.
        # In Java: result.getData()
        return response.json()["data"]
