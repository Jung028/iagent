from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from iagent.config import settings


class AuthMiddleware(BaseHTTPMiddleware):
    """Validates JWT and attaches user_id to request state.

    Every request to /chat must have a valid Bearer token in the Authorization header.
    Health and metrics endpoints are exempt so monitoring tools don't need tokens.
    """

    # EXEMPT_PATHS is a class-level variable (like a static field in Java).
    # We use a "set" (written with curly braces {}) instead of a list because
    # checking membership in a set is O(1) — much faster than a list for lookups.
    # In Java: private static final Set<String> EXEMPT_PATHS = Set.of("/health", "/metrics");
    EXEMPT_PATHS = {"/health", "/metrics"}

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]

        # "in" checks if a value exists in a collection.
        # "request.url.path in self.EXEMPT_PATHS" is like Java's EXEMPT_PATHS.contains(path).
        # Skip auth entirely in local development.
        if settings.app_env == "development":
            return await call_next(request)

        if request.url.path in self.EXEMPT_PATHS:
            # Pass straight through without checking auth.
            return await call_next(request)

        # Read the Authorization header. If missing, .get() returns an empty string "".
        # .removeprefix("Bearer ") strips the "Bearer " prefix from the token string.
        # This is a Python 3.9+ method — in older Python you'd use .replace() or slicing.
        # .strip() removes any leading/trailing whitespace.
        # In Java: header.replace("Bearer ", "").trim()
        token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()

        # "not token" is True when token is an empty string.
        # In Python, empty strings, empty lists, 0, and None are all "falsy" —
        # they evaluate to False in a boolean context. This is different from Java
        # where you must explicitly check: token == null || token.isEmpty()
        if not token:
            # HTTPException tells FastAPI to stop processing and return an HTTP error response.
            # status_code=401 = Unauthorized. "detail" becomes the response body message.
            # In Java Spring: throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "...")
            raise HTTPException(status_code=401, detail="Missing authorization token")

        # TODO: decode and validate JWT, set request.state.user_id
        # Once implemented, this will verify the token's signature, check expiry,
        # and attach the user's ID to request.state for route handlers to use.
        return await call_next(request)
