from typing import Any

from iagent.integrations.base import BaseServiceClient


class IUserClient(BaseServiceClient): 
    async def query_user_info(self, user_id: str, phone_no: str, **ctx: str) -> dict[str, Any]:
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
            "/user/basic/queryUserInfo.json",
            json={
                "userId": user_id, 
                "phoneNo": phone_no,
            },
            user_id=user_id,
            **ctx,
        )

        print(user_id)
        print(response.json())
        response.raise_for_status()

        # The Java service wraps the payload in AccountBizResult<AccountInfoItem>.
        # The actual account data lives in the "data" field.
        # In Java: result.getData()
        return response.json()["result"]