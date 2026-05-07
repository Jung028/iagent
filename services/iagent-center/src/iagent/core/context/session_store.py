import json


class SessionStore:
    """Reads and writes per-user conversation history from Redis."""

    MAX_HISTORY_TURNS = 10
    HISTORY_TTL_SECONDS = 3600

    def __init__(self, redis: object) -> None:
        self._redis = redis

    async def load(self, session_id: str) -> list[dict]:
        """Return stored turns for this session, or [] if none.

        Each turn: {"role": "user"|"assistant", "content": str, "intent": str}
        """
        key = f"session:{session_id}"
        raw: list[bytes] = await self._redis.lrange(key, 0, self.MAX_HISTORY_TURNS - 1)
        return [json.loads(entry) for entry in raw]

    async def append(self, session_id: str, turn: dict) -> None:
        """Append one turn and reset TTL."""
        key = f"session:{session_id}"
        await self._redis.rpush(key, json.dumps(turn))
        await self._redis.ltrim(key, -self.MAX_HISTORY_TURNS, -1)
        await self._redis.expire(key, self.HISTORY_TTL_SECONDS)

    async def clear(self, session_id: str) -> None:
        """Delete the session history (e.g. on explicit user logout)."""
        await self._redis.delete(f"session:{session_id}")

    async def set_state(self, session_id: str, key: str, value: dict) -> None:
        """Store an arbitrary key/value blob for this session (e.g. a pending plan)."""
        redis_key = f"session:{session_id}:state:{key}"
        await self._redis.set(redis_key, json.dumps(value, default=str), ex=self.HISTORY_TTL_SECONDS)

    async def get_state(self, session_id: str, key: str) -> dict | None:
        """Retrieve a stored blob, or None if absent."""
        redis_key = f"session:{session_id}:state:{key}"
        raw = await self._redis.get(redis_key)
        return json.loads(raw) if raw else None

    async def del_state(self, session_id: str, key: str) -> None:
        """Delete a stored blob."""
        await self._redis.delete(f"session:{session_id}:state:{key}")
