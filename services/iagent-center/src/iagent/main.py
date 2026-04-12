# "from contextlib import asynccontextmanager" imports a decorator that lets us
# write startup/shutdown logic using Python's "yield" keyword.
# Think of it as: everything BEFORE yield runs on startup, everything AFTER runs on shutdown.
# In Java Spring Boot this is equivalent to @PostConstruct / @PreDestroy.
from contextlib import asynccontextmanager

# AsyncIterator is a type hint only — it tells other developers (and type checkers)
# what type this async function will produce. It doesn't affect runtime behaviour.
# In Java this would be part of a generic signature like: AsyncIterator<None>
from typing import AsyncIterator

# "import X" brings the whole module in. You then use it as "anthropic.AsyncAnthropic()"
# This is like Java's "import com.anthropic.*" — you keep the namespace prefix.
import anthropic

# "import X as Y" is an alias. We import the redis async library but call it "aioredis"
# so it's clear we're using the async version. In Java you'd just rename the variable.
import redis.asyncio as aioredis

from fastapi import FastAPI

# Import our own modules. The dot-notation matches the folder structure:
# "iagent.api.middleware.auth" = src/iagent/api/middleware/auth.py
from iagent.api.middleware.auth import AuthMiddleware
from iagent.api.middleware.request_id import RequestIDMiddleware
from iagent.api.routes import chat, health
from iagent.config import settings
from iagent.core.intent.classifier import IntentClassifier
from iagent.integrations.iaccount import IAccountClient
from iagent.integrations.ibusiness import IBusinessClient
from iagent.observability.logging import configure_logging
from iagent.observability.metrics import configure_metrics
from iagent.observability.tracing import configure_tracing


# "@asynccontextmanager" is a DECORATOR — it wraps the function below it and adds
# extra behaviour. In Java this is similar to an annotation like @Bean or @Configuration.
#
# "async def" means this is an ASYNCHRONOUS function. Python's async/await is similar
# to Java's CompletableFuture or Spring's @Async, but cleaner to read.
# The "app: FastAPI" part is a type hint — like "FastAPI app" in a Java parameter.
# "-> AsyncIterator[None]" is the return type hint. "None" is Python's equivalent of void.
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # === STARTUP CODE (runs before the server accepts requests) ===

    # Call our observability setup functions (defined in the observability/ folder).
    configure_logging()
    configure_tracing()
    configure_metrics()
    # in main, we create redis and anthropic client instance, then pass into IntentClassifier to identify user's intent
    # then create instance of account and wallet center for later use in chat.py. 

    # Create a Redis client from a connection URL string.
    # "aioredis.from_url()" returns an async Redis client (non-blocking I/O).
    redis = aioredis.from_url(settings.redis_url)

    # Create the Anthropic (Claude) API client with our API key from config.
    anthropic_client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    # Create our IntentClassifier, passing it the Anthropic client and Redis.
    # Then attach it to "app.state" — this is FastAPI's way of storing shared objects
    # that all route handlers can access. In Java Spring this would be @Autowired injection.
    app.state.classifier = IntentClassifier(anthropic_client, redis)

    # Create the two Java backend service clients and store them on app.state too.
    # token_provider=None means M2M auth is not yet implemented (TODO for Sprint 3).
    app.state.account_client = IAccountClient(
        settings.iaccount_base_url, "iaccount", token_provider=None
    )
    app.state.business_client = IBusinessClient(
        settings.ibusiness_base_url, "ibusiness", token_provider=None
    )

    # "yield" is the dividing line between startup and shutdown.
    # The server runs and handles requests while paused here.
    # In Java this is like: server.start(); server.awaitTermination();
    yield

    # === SHUTDOWN CODE (runs after the server stops accepting requests) ===

    # Close the Redis connection pool gracefully.
    await redis.aclose()

    # Close the HTTP connection pools for the Java service clients.
    await app.state.account_client.aclose()
    await app.state.business_client.aclose()


# Create the FastAPI application instance.
# "title" and "version" appear in the auto-generated API docs at /docs.
# "lifespan=lifespan" registers our startup/shutdown function above.
# In Java Spring Boot this is roughly equivalent to the @SpringBootApplication class.
app = FastAPI(title="iAgent Center", version="0.1.0", lifespan=lifespan)

# Register middleware. Middleware wraps EVERY incoming request before it reaches a route.
# FastAPI processes middleware in REVERSE order of registration:
#   1. RequestIDMiddleware runs FIRST (outermost layer)
#   2. AuthMiddleware runs SECOND
# In Java Spring this is a Filter chain / OncePerRequestFilter.
app.add_middleware(RequestIDMiddleware)
app.add_middleware(AuthMiddleware)

# Register route groups (called "routers" in FastAPI).
# health.router handles GET /health and GET /metrics
# chat.router handles POST /chat
# In Java Spring this is like @RestController classes being picked up by component scan.
app.include_router(health.router)
app.include_router(chat.router)
