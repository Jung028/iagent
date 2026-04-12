from typing import Any, Callable, Awaitable

_tools: dict[str, Callable[..., Awaitable[Any]]] = {}


def register(name: str, handler: Callable[..., Awaitable[Any]]) -> None:
    _tools[name] = handler


def get_handler(name: str) -> Callable[..., Awaitable[Any]] | None:
    return _tools.get(name)
