from typing import Any

from iagent.integrations.base import BaseServiceClient


class IAccountClient(BaseServiceClient):
    """HTTP client for the iAccount Java service.

    iAccount owns account metadata — it knows which accounts a user has,
    what type they are, and which wallet is linked to each account.

    Inherits all retry, circuit breaker, and auth logic from BaseServiceClient.
    In Java: public class IAccountClient extends BaseServiceClient { ... }
    """

    async def get_account_by_user_id(self, user_id: str, **ctx: str) -> dict[str, Any]:
        """Fetch the single account belonging to a user (1:1 relationship).

        Calls POST /account/basic/queryAccountInfoByUserId.json on the account center.
        The response is wrapped in AccountBizResult<AccountInfoItem>; we extract .data.

        Returns a single account dict, e.g.:
        {"accountId": "acc-1", "userId": "u-1", "status": "ACTIVE", ...}
        """

        # POST with a JSON body — matches @PostMapping + @RequestBody on the Java side.
        # json={"userId": user_id} serialises the dict as the request body.
        # In Java: QueryAccountInfoRequest request = new QueryAccountInfoRequest(userId)
        response = await self._request(
            "POST",
            "/account/basic/queryAccountInfoByUserId.json",
            json={"userId": user_id},
            user_id=user_id,
            **ctx,
        )

        response.raise_for_status()

        # The Java service wraps the payload in AccountBizResult<AccountInfoItem>.
        # The actual account data lives in the "data" field.
        # In Java: result.getData()
        return response.json()["data"]

    async def get_account_details(self, account_id: str, **ctx: str) -> dict[str, Any]:
        """Fetch details for a single account by its ID.

        Returns a single account dict. Not used by the balance flow today,
        but available for future features.
        """
        response = await self._request("GET", f"/accounts/{account_id}", **ctx)
        response.raise_for_status()
        return response.json()
