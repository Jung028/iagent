from typing import Any

from iagent.integrations.base import BaseServiceClient


class IBusinessClient(BaseServiceClient):
    """HTTP client for the iBusiness Java service.

    iBusiness is the source of financial truth for balance and transaction data.
    All balance queries and transfer operations go through this service.

    Corresponds to BusinessBasicController on the Java side.
    Inherits all retry, circuit breaker, and auth logic from BaseServiceClient.
    """

    async def query_balance(self, account_id: str, **ctx) -> dict[str, Any]:
        response = await self._request(
            "POST",
            "/business/basic/queryBalance.json",
            json={"accountId": account_id},
            **ctx,
        )

        response.raise_for_status()

        payload = response.json()
        result = payload.get("result", {})

        # ❗ enforce business success
        if not payload.get("success") or result.get("success") is False:
            raise ValueError(f"Balance query failed: {payload}")

        return {
            "currency": result.get("currency"),
            "balance": result.get("balance", 0.0),
            "pending": 0.0,
        }
    
    async def query_transaction_details(self, account_id: str, txn_id: str, **ctx: str) -> dict[str, Any] :
        response = await self._request(
            "POST",
            "/business/basic/queryTransactionDetails.json",
            json={"accountId": account_id,
                  "txnId": txn_id,},
            **ctx,
        )
        response.raise_for_status()
        payload = response.json()
        result = payload.get("result", {})

        # ❗ enforce business success
        if not payload.get("success") or result.get("success") is False:
            raise ValueError(f"Balance query failed: {payload}")
        
        return {
            "transaction_id": result.get("txnId"),
            "payer_account_id": result.get("payerAccountId"),
            "payee_account_id": result.get("payeeAccountId"),
            "amount": float(result.get("amount", 0.0)),
            "currency": result.get("currency", "MYR"),
            "txn_type": result.get("txnType"),
            "txn_status": result.get("txnStatus"),
            "failure_reason": result.get("failureReason"),
            "created_at": result.get("gmtCreate"),
            "completed_at": result.get("gmtComplete"),
        }
    