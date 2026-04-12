from typing import Any

from iagent.integrations.base import BaseServiceClient


class IWalletClient(BaseServiceClient):
    """HTTP client for the iWallet Java service.

    iWallet is the source of financial truth — it owns wallet balances and
    transaction history. iAgent Center never reads financial data directly from
    the database; it always goes through this service client.

    Inherits all retry, circuit breaker, and auth logic from BaseServiceClient.
    """

    async def get_balance(self, wallet_id: str, **ctx: str) -> dict[str, Any]:
        """Fetch the current balance for a wallet.

        Returns a dict like:
        {"currency": "USD", "available": 250.00, "pending": 0.0}

        "available" = funds the user can spend right now.
        "pending"   = funds reserved by in-progress transactions (not yet settled).
        """
        response = await self._request("GET", f"/wallets/{wallet_id}/balance", **ctx)
        response.raise_for_status()
        return response.json()

    async def get_transactions(
        self,
        wallet_id: str,
        limit: int = 50,            # Default parameter: if not provided, fetch 50 transactions.
                                    # In Java you'd need an overloaded method for this.
        from_date: str | None = None,   # "str | None" = Optional<String> in Java.
                                        # None is Python's null — the default means "no date filter".
        **ctx: str,
    ) -> list[dict[str, Any]]:
        """Fetch transaction history for a wallet.

        Not used by the balance inquiry flow, but available for future
        spending insights features.
        """

        # Build a query params dict. Start with just limit.
        # In Java: Map<String, Object> params = new HashMap<>(); params.put("limit", limit);
        params: dict[str, Any] = {"limit": limit}

        # Only add "from_date" to the params if it was provided.
        # "if from_date:" evaluates to True for any non-None, non-empty string.
        if from_date:
            params["from_date"] = from_date

        response = await self._request(
            "GET",
            f"/wallets/{wallet_id}/transactions",
            params=params,   # httpx will append these as URL query params: ?limit=50&from_date=...
            **ctx,
        )
        response.raise_for_status()
        return response.json()
