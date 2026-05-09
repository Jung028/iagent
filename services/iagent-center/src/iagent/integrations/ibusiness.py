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
    
    async def transfer_init(
        self,
        payer_account_id: str,
        payee_account_id: str,
        amount: float,
        currency: str,
        unique_request_id: str,
        transfer_type: str = "AUTH_TRANSFER",
        qr_token: str = "",
        **ctx: Any,
    ) -> str:
        """Call transferInit — returns the transferToken needed for transferConfirm."""
        response = await self._request(
            "POST",
            "/business/basic/transferInit.json",
            json={
                "payerAccountNo":  payer_account_id,
                "payeeAccountNo":  payee_account_id,
                "amount":          {"amount": amount, "currency": currency},
                "uniqueRequestId": unique_request_id,
                "transferType":    transfer_type,
                "qrToken":         qr_token,
            },
            **ctx,
        )
        response.raise_for_status()
        payload = response.json()
        if not payload.get("success"):
            raise ValueError(f"transferInit failed: {payload.get('resultMessage', payload)}")
        result = payload.get("result", "")
        # Backend may return the token directly as a string, or wrapped in {"transferToken": "..."}
        if isinstance(result, str):
            return result
        return str(result.get("transferToken", ""))

    async def transfer_confirm(
        self,
        account_id: str,
        password: str,
        transfer_token: str,
        transfer_type: str = "TRANSFER",
        **ctx: Any,
    ) -> dict[str, Any]:
        """Call transferConfirm with the user's PIN — finalises the transfer."""
        response = await self._request(
            "POST",
            "/business/basic/transferConfirm.json",
            json={
                "accountId":     account_id,
                "password":      password,
                "transferType":  transfer_type,
                "transferToken": transfer_token,
            },
            **ctx,
        )
        response.raise_for_status()
        payload = response.json()
        if not payload.get("success"):
            raise ValueError(f"transferConfirm failed: {payload.get('resultMessage', payload)}")
        result = payload.get("result", {})
        return {
            "status":   "success",
            "txid":     result.get("txnId", ""),
            "amount":   result.get("amount"),
            "currency": result.get("currency", "MYR"),
        }

    async def query_transaction_history(self, account_id: str, params: dict, **ctx:Any) -> list[dict[str, Any]]: 

        response = await self._request(
            "POST",
            "/business/basic/queryTransactionHistory.json",
            # add more params for transaction history query. time range etc. 
            json={"accountId":account_id,
                  **params,
                  },
            **ctx,
        )
        response.raise_for_status()
        payload = response.json() 
        result = payload.get("result") or {}
        transactions = result.get("transactions") or []
        return [
            {
                "txnId": t.get("txnId"),
                "gmtCreate": t.get("gmtCreate"),
                "amount": t.get("amount"),
                "payeeAccountId": t.get("payeeAccountId"),
                "transactionType": t.get("transactionType"),
                "gmtCompleted": t.get("gmtCompleted"),
                "currency": t.get("currency"),
                "status": t.get("status"),
                "extInfo": t.get("extInfo"),
            }
            for t in transactions
        ]
    