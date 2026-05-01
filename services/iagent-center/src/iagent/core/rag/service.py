from __future__ import annotations
 
import json
from typing import Any
 
import structlog
from openai import AsyncOpenAI
 
log = structlog.get_logger(__name__)
 
# Embedding model — text-embedding-3-small is cheapest and fast enough.
# Output dimension: 1536 — must match vector(1536) in schema.py
EMBEDDING_MODEL = "text-embedding-3-small"
 
# How many past interactions to retrieve per request.
# 5 is enough context without bloating the LLM prompt.
TOP_K_HISTORY = 5
 

"""
rag/service.py
 
RAG Memory Service — the long-term brain of iAgent.
 
Two public methods:
  get_context(user_id, message) → dict
      Called BEFORE the LLM sees the message.
      Returns enriched context: profile + contacts + entities + relevant history.
 
  store(user_id, intents, entities, result)
      Called AFTER the orchestrator finishes.
      Saves the interaction to PostgreSQL + pgvector for future retrieval.
 
Dependencies:
  pip install asyncpg pgvector openai redis structlog
 
Environment variables:
  OPENAI_API_KEY       — for text embeddings
  DATABASE_URL         — asyncpg PostgreSQL connection string
  REDIS_URL            — Redis connection string
"""


class RAGService : 
    """RAG Memory Service.
 
    Injected into app.state on startup so all route handlers share one instance.
    Holds a single asyncpg pool and a Redis client — both are async-safe.
 
    In main.py / lifespan:
        from iagent.services.rag.service import RAGService
 
        rag = RAGService(pool=db_pool, redis=redis_client)
        app.state.rag_service = rag
    """
    def __init__(self, pool, redis) -> None: 
        #Asyncpg connection pool, shared across all requests 
        self._pool = pool 
        self._redis = redis 
        # open ai only used for the embeddings 
        self._openai = AsyncOpenAI()

    async def get_context(self, user_id: str, message: str) -> dict[str, Any] : 
        """Fetch and return all context needed for this user + message.
 
        Called in chat.py BEFORE classifier.classify() so the LLM
        already has full context when it reads the message.
 
        Returns:
            {
                "profile":   { timezone, currency, language, preferences },
                "entities":  { "landlord": { name, walletId }, "Ali": {...} },
                "contacts":  [ { alias, name, walletId, phone } ],
                "history":   [ { message, intents, result }, ... ],  # top 5 relevant
                "session":   { ... }   # last interaction in this session
            }
        """
        # we want to get context, which is query all the context types, which is profile infomration 
        # etc. all is query from the databse, but we need to update the postgresql to add the vector 