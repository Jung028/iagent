from typing import Any

from iagent.integrations.base import BaseServiceClient


class IUserClient(BaseServiceClient): 
    async def query_user_info(self, user_id: str, phone_no: str | None = None, **ctx: str) -> dict[str, Any]:
        """Fetch the single account belonging to a user (1:1 relationship).

        Calls POST /user/basic/queryUserInfo.json on the user center.
        
        Returns user info including account details.
        """

        # POST with a JSON body — matches @PostMapping + @RequestBody on the Java side.
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

        response.raise_for_status()

        # The actual user data lives in the "result" field.
        return response.json()["result"]