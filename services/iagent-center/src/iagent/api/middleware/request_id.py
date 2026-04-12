import uuid  # Python's built-in library for generating UUIDs (like java.util.UUID)

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


# "class RequestIDMiddleware(BaseHTTPMiddleware)" inherits from BaseHTTPMiddleware.
# This is the standard way to write middleware in FastAPI/Starlette.
# In Java Spring this would be: public class RequestIDFilter implements OncePerRequestFilter
class RequestIDMiddleware(BaseHTTPMiddleware):
    """Attaches X-Request-ID to every request and response.

    This gives every HTTP request a unique ID so that, if something goes wrong,
    you can search logs across iAgent Center AND the Java backend services
    using the same ID to trace the full journey of a single request.
    """

    # "async def dispatch()" is the method called by the framework for every request.
    # It receives:
    #   - request: the incoming HTTP request object
    #   - call_next: a callable (function reference) that runs the next layer in the chain
    #                (either the next middleware or the actual route handler)
    # In Java this is: filterChain.doFilter(request, response)
    #
    # "# type: ignore[override]" suppresses a mypy warning about the type signature
    # not exactly matching the parent class — safe to ignore here.
    async def dispatch(self, request: Request, call_next):  # type: ignore[override]

        # Try to read X-Request-ID from the incoming request headers.
        # request.headers is a dict-like object — .get("key", default) returns the value
        # or the default if the key is missing.
        # If the mobile app didn't send one, we generate a fresh UUID.
        # str(uuid.uuid4()) produces something like: "550e8400-e29b-41d4-a716-446655440000"
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

        # Store the request_id on request.state so other parts of the code
        # (route handlers, tools) can read it without passing it as a parameter everywhere.
        # request.state is a simple bag of attributes — you can put anything on it.
        # In Java Spring this is like using RequestContextHolder or MDC.
        request.state.request_id = request_id

        # "await call_next(request)" passes control to the next layer (middleware or route).
        # "await" pauses this function until call_next finishes, then continues.
        # In Java: CompletableFuture.get() — but non-blocking (thread is freed while waiting).
        response = await call_next(request)

        # After the route handler has finished and built a response,
        # we add X-Request-ID to the response headers too.
        # This lets the mobile app read the ID for its own logging.
        response.headers["X-Request-ID"] = request_id

        # Return the response back up the middleware chain.
        return response
