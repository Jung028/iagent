import json
import structlog

log = structlog.get_logger(__name__)

# Fields projected from iAccount response into the lightweight profile.
_ACCOUNT_FIELDS = {"accountId", "status", "currency", "kycTier", "features"}


class ProfileLoader:
    """Loads a lightweight user profile from cache or iAccount service."""

    PROFILE_TTL_SECONDS = 300

    def __init__(self, redis: object, account_client: object) -> None:
        self._redis = redis
        self._account_client = account_client

    async def load(self, user_id: str) -> dict | None:
        """Return cached profile dict, or fetch from iAccount on cache miss.

        Returns None if both cache and service call fail (non-fatal — callers
        should treat a missing profile as degraded, not an error).
        """
        key = f"profile:{user_id}"

        cached = await self._redis.get(key)
        if cached:
            return json.loads(cached)

        try:
            account = await self._account_client.get_account_by_user_id(user_id)
            profile = {k: account[k] for k in _ACCOUNT_FIELDS if k in account}
            await self._redis.set(key, json.dumps(profile), ex=self.PROFILE_TTL_SECONDS)
            return profile
        except Exception as exc:
            log.warning("profile_load_failed", user_id=user_id, error=str(exc))
            return None
