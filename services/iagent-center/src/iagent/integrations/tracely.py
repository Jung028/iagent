from typing import Any

from iagent.integrations.base import BaseServiceClient


class TracelyGraphClient(BaseServiceClient):
    """Reads the unified system graph from Tracely's graph API.

    Reuses BaseServiceClient so every graph query carries the same X-Trace-Id /
    X-Request-ID correlation headers as the rest of the agent's calls.
    """

    async def find(self, query: str, **ctx: str) -> dict[str, Any]:
        """Resolve a fuzzy name to canonical graph entities."""
        r = await self._request("GET", "/api/graph/find", params={"q": query}, **ctx)
        return r.json()

    async def describe(self, entity_id: str, **ctx: str) -> dict[str, Any]:
        """What an entity is, plus its direct calls / callers and provenance."""
        r = await self._request("GET", "/api/graph/describe", params={"id": entity_id}, **ctx)
        return r.json()

    async def neighbors(
        self,
        entity_id: str,
        direction: str = "both",
        kinds: list[str] | None = None,
        **ctx: str,
    ) -> dict[str, Any]:
        """One-hop traversal: who calls / is called by an entity."""
        params: dict[str, str] = {"id": entity_id, "dir": direction}
        if kinds:
            params["kinds"] = ",".join(kinds)
        r = await self._request("GET", "/api/graph/neighbors", params=params, **ctx)
        return r.json()

    async def blast_radius(self, entity_id: str, depth: int = 3, **ctx: str) -> dict[str, Any]:
        """Everything reachable downstream — the impact of changing this entity."""
        r = await self._request(
            "GET", "/api/graph/blast-radius", params={"id": entity_id, "depth": str(depth)}, **ctx
        )
        return r.json()
