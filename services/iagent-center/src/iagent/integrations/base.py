"""Base HTTP client shared by all Java backend service integrations.

All four Java services (iAccount, iWallet, etc.) need the same cross-cutting concerns:
  - Retry logic on server errors
  - Circuit breaker to stop hammering a failing service
  - Auth headers on every request
  - Correlation IDs for distributed tracing

Rather than duplicating this in every client, we put it here in a base class
and let IAccountClient, IWalletClient etc. inherit it.
In Java Spring this would be a shared RestTemplate / WebClient configuration bean.
"""
import asyncio  # Python's standard library for async programming (event loops, sleep, etc.)
from typing import Any

import httpx    # Third-party async HTTP client library — like Java's WebClient (reactive) or OkHttp
import structlog

log = structlog.get_logger(__name__)

# A Python "set" of HTTP status codes that warrant a retry.
# We only retry on server errors (5xx). We never retry on 4xx (client errors)
# because retrying a 404 or 401 won't fix the problem.
_RETRY_STATUSES = {500, 502, 503, 504}
_MAX_RETRIES = 3


class CircuitBreaker:
    """Prevents repeated calls to a failing service.

    The circuit breaker has three states:
    - CLOSED (normal):  requests go through
    - OPEN (failing):   requests are rejected immediately for RECOVERY_TIMEOUT_SECONDS
    - HALF-OPEN (recovering): after timeout, one request goes through to test recovery

    This pattern stops iAgent Center from flooding a struggling Java service with requests,
    giving it time to recover. In Java this is the Resilience4j CircuitBreaker.
    """

    FAILURE_THRESHOLD = 5       # How many consecutive failures before opening the circuit
    RECOVERY_TIMEOUT_SECONDS = 30   # How long to wait before trying again after opening

    def __init__(self, service: str) -> None:
        self.service = service      # Name used in log messages (e.g. "iaccount")
        self._failures = 0          # Counter of consecutive failures
        self._open_until: float = 0.0   # Timestamp (epoch seconds) when circuit can close again.
                                        # float type because asyncio uses float timestamps.

    def is_open(self) -> bool:
        """Returns True if the circuit is open (all requests should be rejected)."""

        # "self._open_until" is 0.0 when the circuit is closed (never opened).
        # "asyncio.get_event_loop().time()" returns the current time as a float (epoch seconds).
        # If the current time is still before _open_until, the circuit is still open.
        if self._open_until and asyncio.get_event_loop().time() < self._open_until:
            return True
        return False

    def record_success(self) -> None:
        """Called after a successful HTTP response — resets the failure counter."""
        self._failures = 0
        self._open_until = 0.0  # Close the circuit (reset to 0 = "never opened")

    def record_failure(self) -> None:
        """Called after a failed HTTP response — increments counter, opens circuit if threshold hit."""
        self._failures += 1  # "+= 1" increments in place — like Java's failures++

        # ">=" means "greater than or equal to" — same as Java.
        if self._failures >= self.FAILURE_THRESHOLD:
            # Set _open_until to "now + 30 seconds" — circuit is open until then.
            self._open_until = asyncio.get_event_loop().time() + self.RECOVERY_TIMEOUT_SECONDS
            log.error("circuit_breaker_opened", service=self.service)


class BaseServiceClient:
    """Shared HTTP client with retry, circuit breaker, auth, and correlation headers.

    Subclasses (IAccountClient, IWalletClient) call self._request() and get all of this
    behaviour for free without repeating it.
    In Java: an abstract base class with a protected WebClient field.
    """

    def __init__(self, base_url: str, service_name: str, token_provider: Any) -> None:
        # .rstrip("/") removes trailing slashes from the URL so we don't get double-slashes
        # when we append paths like "/users/123". In Java: baseUrl.replaceAll("/$", "")
        self._base_url = base_url.rstrip("/")
        self._service_name = service_name
        self._token_provider = token_provider  # Will provide M2M JWT tokens (TODO)

        # One CircuitBreaker instance per service — tracks failures for this specific service.
        self._circuit = CircuitBreaker(service_name)

        # httpx.AsyncClient is a connection-pool-backed async HTTP client.
        # "base_url" is prepended to all relative paths automatically.
        # "timeout=10.0" means any request that takes more than 10 seconds is cancelled.
        # In Java: WebClient.builder().baseUrl(url).build()
        self._http = httpx.AsyncClient(base_url=self._base_url, timeout=10.0)

    async def _request(
        self,
        method: str,        # HTTP method: "GET", "POST", etc.
        path: str,          # URL path, e.g. "/users/123/accounts"
        *,                  # Everything after "*," MUST be passed as keyword arguments.
                            # This prevents callers from accidentally passing args in wrong order.
                            # In Java you'd use a builder pattern for this.
        request_id: str = "",   # Correlation ID for distributed tracing
        user_id: str = "",      # Forwarded to Java services for their own audit logs
        workflow_id: str = "",  # Future use — for multi-step workflow tracing
        **kwargs: Any,      # "**kwargs" captures any additional keyword arguments
                            # (like "json=", "params=") and forwards them to httpx.
                            # In Java: you'd have overloaded methods or a request options object.
    ) -> httpx.Response:
        """Make an authenticated HTTP request with retry and circuit breaker logic."""

        # Bail out immediately if the circuit is open — don't even try the request.
        if self._circuit.is_open():
            raise RuntimeError(f"Circuit open for {self._service_name}")
            # f-string: f"Circuit open for {self._service_name}"
            # In Java: "Circuit open for " + this.serviceName

        # Build the headers dict to send with every request.
        # TODO: self._token_provider.get_token() will be awaited once implemented.
        headers = {
            "Authorization": f"Bearer {await self._token_provider.get_token()}",
            "X-Request-ID": request_id,   # For end-to-end trace correlation
            "X-User-ID": user_id,         # For Java service audit logging
            "X-Workflow-ID": workflow_id,
        }

        # Retry loop: attempt the request up to _MAX_RETRIES times.
        # "range(1, _MAX_RETRIES + 1)" produces [1, 2, 3] — attempt numbers start at 1.
        # In Java: for (int attempt = 1; attempt <= MAX_RETRIES; attempt++)
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                # Make the HTTP request. "**kwargs" unpacks any extra args (json, params, etc.)
                # as additional keyword arguments to .request().
                response = await self._http.request(method, path, headers=headers, **kwargs)

                # If we got a server error AND we still have retries left, wait and try again.
                # "and" is Python's boolean AND operator — same as Java's &&.
                if response.status_code in _RETRY_STATUSES and attempt < _MAX_RETRIES:
                    # Exponential backoff: wait 0.5s, then 1s, then 2s between retries.
                    # "2 ** (attempt - 1)" = 2^0=1, 2^1=2, 2^2=4 → × 0.5 = 0.5, 1.0, 2.0
                    # "await asyncio.sleep()" pauses without blocking other requests.
                    # In Java: Thread.sleep() — but that blocks the thread; this doesn't.
                    await asyncio.sleep(0.5 * 2 ** (attempt - 1))
                    continue  # "continue" jumps back to the top of the for loop (next attempt)

                # Response received (even if it's a 4xx/5xx — we don't retry those).
                if response.is_success:
                    self._circuit.record_success()
                else:
                    self._circuit.record_failure()

                return response  # Return the response to the subclass (e.g. IAccountClient)

            except httpx.TransportError as exc:
                # TransportError covers network-level failures (connection refused, DNS failure, etc.)
                # "except ExceptionType as variable_name:" is like Java's "catch (ExceptionType e)"
                self._circuit.record_failure()
                if attempt == _MAX_RETRIES:
                    raise   # "raise" without arguments re-raises the current exception
                            # In Java: throw e;  (but "raise" alone is cleaner — preserves traceback)
                await asyncio.sleep(0.5 * 2 ** (attempt - 1))

        # This line should never be reached (the loop always returns or raises).
        # "raise RuntimeError()" creates and raises a new exception — like Java's "throw new RuntimeException()"
        raise RuntimeError("Unreachable")

    async def aclose(self) -> None:
        """Close the underlying HTTP connection pool. Called at app shutdown."""
        await self._http.aclose()
