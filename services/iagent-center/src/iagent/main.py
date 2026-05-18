# "from contextlib import asynccontextmanager" imports a decorator that lets us
# write startup/shutdown logic using Python's "yield" keyword.
# Think of it as: everything BEFORE yield runs on startup, everything AFTER runs on shutdown.
# In Java Spring Boot this is equivalent to @PostConstruct / @PreDestroy.
import os
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
from iagent.core.orchestrator.agents.planning_agent import PlanningAgent
from iagent.core.orchestrator.agents.read_agent import ReadAgent
from iagent.core.orchestrator.agents.write_agent import WriteAgent
from iagent.core.orchestrator.agents.synthesize_agent import SynthesizeAgent
from iagent.core.validator.intent_validator import IntentValidator
from iagent.services.rag.database import create_engine_and_factory, create_tables
from iagent.services.rag.rag_service import RAGService
import redis.asyncio as aioredis

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import our own modules. The dot-notation matches the folder structure:
# "iagent.api.middleware.auth" = src/iagent/api/middleware/auth.py
from iagent.api.middleware.auth import AuthMiddleware
from iagent.api.middleware.request_id import RequestIDMiddleware
from iagent.api.routes import chat, health, threads, extract, reconciliation
from iagent.services.document.ocr_service import OCRService
from iagent.services.document.llm_extraction_service import LLMExtractionService
from iagent.api.controllers.extract_controller import ExtractionController
from iagent.api.controllers.reconciliation_controller import ReconciliationController
from iagent.services.document.reconciliation_service import ReconciliationService
from iagent.config import settings
from iagent.core.intent.classifier import IntentClassifier
from iagent.integrations.iaccount import IAccountClient
from iagent.integrations.ibusiness import IBusinessClient
from iagent.integrations.iuser import IUserClient
from iagent.observability.logging import configure_logging
from iagent.observability.metrics import configure_metrics
from iagent.observability.tracing import configure_tracing
from iagent.core.orchestrator import Orchestrator
from iagent.core.models.intent import Intent
from iagent.core.context.session_store import SessionStore
from iagent.core.context.profile_loader import ProfileLoader
from iagent.integrations.platforms.registry import PlatformRegistry
from iagent.integrations.platforms.whatsapp import WhatsAppAdapter
from iagent.integrations.platforms.whatsapp.client import WhatsAppClient
from iagent.integrations.platforms.whatsapp.verifier import WhatsAppWebhookVerifier
from iagent.api.routes.webhooks import whatsapp as whatsapp_webhook


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

    # Create the Anthropic async client for intent classification.
    anthropic_client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    # Create our IntentClassifier, passing it the Anthropic client and Redis.
    # Then attach it to "app.state" — this is FastAPI's way of storing shared objects
    # that all route handlers can access. In Java Spring this would be @Autowired injection.
    app.state.classifier = IntentClassifier(anthropic_client, redis)
    app.state.anthropic_client = anthropic_client

    # Create the two Java backend service clients and store them on app.state too.
    # token_provider=None means M2M auth is not yet implemented (TODO for Sprint 3).
    app.state.account_client = IAccountClient(
        settings.iaccount_base_url, "iaccount", token_provider=None
    )
    app.state.business_client = IBusinessClient(
        settings.ibusiness_base_url, "ibusiness", token_provider=None
    )
    app.state.user_client = IUserClient(
        settings.iuser_base_url, "iuser", token_provider=None
    )

    # Wire up context services.
    # ProfileLoader gets its OWN IAccountClient instance so that connection
    # failures in profile loading don't open the circuit breaker used by
    # BalanceInquiryHandler and other handlers.
    profile_account_client = IAccountClient(
        settings.iaccount_base_url, "iaccount-profile", token_provider=None
    )
    app.state.session_store = SessionStore(redis)
    app.state.profile_loader = ProfileLoader(redis, profile_account_client)

    # Wire up the four agents for the three-phase orchestration flow:
    #   Phase 1 — PlanningAgent  : decomposes user message into ordered action steps
    #   Phase 2 — ReadAgent      : fetches data from the ledger (researcher)
    #             WriteAgent     : executes mutations after user confirmation (executor)
    #   Phase 3 — SynthesizeAgent     : synthesizes all results into a friendly reply
    planning_agent = PlanningAgent(anthropic_client)
    read_agent     = ReadAgent()
    write_agent    = WriteAgent()
    synthesize_agent    = SynthesizeAgent(anthropic_client)

    app.state.orchestrator = Orchestrator(
        planning_agent=planning_agent,
        read_agent=read_agent,
        write_agent=write_agent,
        synthesize_agent=synthesize_agent,
        account_client=app.state.account_client,
        business_client=app.state.business_client,
        user_client=app.state.user_client,
        session_store=app.state.session_store,
    )

    # Wire up WhatsApp platform adapter.
    whatsapp_client = WhatsAppClient(
        phone_number_id=settings.whatsapp_phone_number_id,
        access_token=settings.whatsapp_access_token,
    )
    whatsapp_verifier = WhatsAppWebhookVerifier(
        verify_token=settings.whatsapp_verify_token,
        app_secret=settings.whatsapp_app_secret,
    )
    app.state.whatsapp_adapter = WhatsAppAdapter(whatsapp_client, whatsapp_verifier)

    app.state.extraction_controller = ExtractionController(
        ocr_service=OCRService(anthropic_client),
        llm_service=LLMExtractionService(anthropic_client),
    )

    app.state.reconciliation_controller = ReconciliationController(
        reconciliation_service=ReconciliationService(anthropic_client),
    )

    platform_registry = PlatformRegistry()
    platform_registry.register(app.state.whatsapp_adapter)
    app.state.platform_registry = platform_registry

    # Wire up RAG memory service — optional. Server starts without it if either
    # DATABASE_URL or OPENAI_API_KEY is missing; RAG-dependent features are disabled.
    app.state.rag_service = None
    rag_engine = None
    if not settings.database_url:
        import structlog as _log
        _log.get_logger(__name__).warning("rag_disabled", reason="DATABASE_URL not set in .env")
    # elif not settings.openai_api_key:
    #     import structlog as _log
    #     _log.get_logger(__name__).warning("rag_disabled", reason="OPENAI_API_KEY not set in .env")
    else:
        rag_engine, rag_session_factory = create_engine_and_factory()
        await create_tables(rag_engine)
        app.state.rag_service = RAGService(
            session_factory=rag_session_factory,
            redis=redis,
            user_client=app.state.user_client,
            anthropic_client=anthropic_client,
        )

    # "yield" is the dividing line between startup and shutdown.
    # The server runs and handles requests while paused here.
    # In Java this is like: server.start(); server.awaitTermination();
    yield

    # === SHUTDOWN CODE (runs after the server stops accepting requests) ===

    # Close the Redis connection pool gracefully.
    await redis.aclose()

    # Dispose the RAG database engine connection pool (only if RAG was initialised).
    if rag_engine is not None:
        await rag_engine.dispose()

    # Close the HTTP connection pools for the Java service clients.
    await app.state.account_client.aclose()
    await app.state.business_client.aclose()
    await app.state.user_client.aclose()
    await profile_account_client.aclose()
    await whatsapp_client.aclose()


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
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8089", "http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(AuthMiddleware)

# Register route groups (called "routers" in FastAPI).
# health.router handles GET /health and GET /metrics
# chat.router handles POST /chat
# In Java Spring this is like @RestController classes being picked up by component scan.
app.include_router(health.router)
app.include_router(chat.router)
app.include_router(threads.router)
app.include_router(whatsapp_webhook.router)
app.include_router(extract.router)
app.include_router(reconciliation.router)
