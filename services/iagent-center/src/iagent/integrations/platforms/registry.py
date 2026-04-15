from iagent.integrations.platforms.base import BasePlatformAdapter


class PlatformRegistry:
    """Maps platform name strings to their adapter instances.

    Registered once at startup in main.py lifespan.
    Used by webhook routes to look up the correct adapter per request.
    """

    def __init__(self) -> None:
        self._adapters: dict[str, BasePlatformAdapter] = {}

    def register(self, adapter: BasePlatformAdapter) -> None:
        """Register an adapter. Raises on duplicate platform names."""
        name = adapter.platform_name
        if name in self._adapters:
            raise ValueError(f"Adapter already registered for platform '{name}'")
        self._adapters[name] = adapter

    def get(self, platform: str) -> BasePlatformAdapter:
        """Return the adapter for platform, or raise KeyError if unregistered."""
        # TODO: return a NullAdapter (logs + no-ops) instead of raising, for graceful degradation
        return self._adapters[platform]
