# iAgent Center

The AI orchestration service for the iAgent platform. Receives chat messages from any connected platform (WhatsApp, web), classifies intent, runs a three-phase agent pipeline, and returns structured responses to the frontend.

---
## System Analysis 

Full system design and analysis is attatched here : 
https://www.notion.so/AI-Chatbot-iagent-SA-33fd911b2cdb80da88f5fc3e332c51ba?source=copy_link


## Architecture

```
Client / Platform
      │
      ▼
┌─────────────────────────────────────────────────────┐
│                   FastAPI Server                    │
│                                                     │
│  POST /chat                                         │
│       │                                             │
│       ▼                                             │
│  IntentClassifier  ──► Redis (cache)                │
│       │                                             │
│       ▼                                             │
│  Orchestrator  (three-phase pipeline)               │
│  ┌────────────────────────────────────────────┐     │
│  │  Phase 1 — PlanningAgent                  │     │
│  │            Decomposes message into steps  │     │
│  │                    │                      │     │
│  │  Phase 2 — ReadAgent  /  WriteAgent       │     │
│  │            Executes each step via tools   │     │
│  │                    │                      │     │
│  │  Phase 3 — SynthesisAgent                     │     │
│  │            Synthesises reply              │     │
│  └────────────────────────────────────────────┘     │
│       │                                             │
│       ▼                                             │
│  ResponseBuilder  (text + UI cards)                 │
└─────────────────────────────────────────────────────┘
      │
      ▼
  iAccount / iBusiness / iUser  (Java backends)
```

### Intent types

| Intent | Description |
|---|---|
| `READ` | Balance inquiries, transaction history, spending analysis |
| `TRANSFER` | Fund transfers between accounts |
| `TOP_UP` | Account top-up / reload |
| `EXPENSE_TRACKING` | Categorise and track expenses |
| `PHOTO_CLAIM` | Submit a photo-based claim |
| `RECURRING_PAYMENT` | Manage recurring payments |

---

## Balance pipeline (TASK-001)

A real-time financial reconciliation pipeline that watches Gmail for invoices and CommBank for matching transactions, then writes double-entry journal entries automatically.

```
Gmail inbox  ──► Pub/Sub push ──► /webhooks/gmail
                                        │
                                   GmailService
                                        │
                                   Invoice stored
                                        │
CommBank ──► Basiq CDR ──► /webhooks/basiq
                                   BasiqService
                                        │
                              Transaction stored
                                        │
                               MatchingEngine
                           (amount 50% + date 30% + vendor 20%)
                                        │
                              score ≥ 0.85 → AUTO
                                        │
                               JournalWriter
                          DR Expense / DR GST / CR Bank
```

### Journal entry example — $110 inc-GST invoice

| Account | Code | Debit | Credit |
|---|---|---|---|
| Expense | 6-1000 | $100.00 | |
| GST Paid | 2-2000 | $10.00 | |
| Bank | 1-1000 | | $110.00 |

---

## Getting started

### Prerequisites

- Python 3.12+
- PostgreSQL with pgvector extension
- Redis

### Install

```bash
pip install -e ".[dev]"
```

### Configure

Copy `.env.example` to `.env` and fill in the required values:

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-...
IACCOUNT_BASE_URL=http://localhost:8887
IBUSINESS_BASE_URL=http://localhost:8180
IUSER_BASE_URL=http://localhost:8085

# Optional — RAG memory
DATABASE_URL=postgresql://user@localhost:5432/agent

# Optional — Gmail / Balance pipeline
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
PUBSUB_TOPIC=projects/PROJECT_ID/topics/gmail-push

# Optional — WhatsApp
WHATSAPP_PHONE_NUMBER_ID=...
WHATSAPP_ACCESS_TOKEN=...
WHATSAPP_APP_SECRET=...
```

### Run

```bash
uvicorn iagent.main:app --reload --port 8000
```

API docs available at `http://localhost:8000/docs`.

---

## Key endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/chat` | Send a message; returns text + optional UI cards |
| `GET` | `/threads/{thread_id}` | Retrieve conversation thread |
| `GET` | `/health` | Health check |
| `GET` | `/onboarding/gmail/start` | Begin Gmail OAuth flow |
| `GET` | `/onboarding/gmail/callback` | OAuth callback (redirect target) |
| `POST` | `/webhooks/gmail` | Google Pub/Sub push receiver |
| `POST` | `/webhooks/basiq` | Basiq transaction webhook receiver |
| `POST` | `/webhooks/whatsapp` | WhatsApp Cloud API webhook |

---

## Project structure

```
src/iagent/
├── api/
│   ├── middleware/         # Auth (JWT), request ID injection
│   ├── routes/
│   │   ├── chat.py         # POST /chat
│   │   ├── threads.py      # Thread history
│   │   ├── onboarding.py   # Gmail OAuth onboarding
│   │   └── webhooks/       # WhatsApp, Gmail, Basiq receivers
│   └── schemas/            # Pydantic request/response models
│
├── core/
│   ├── intent/             # Intent classification (Anthropic API)
│   ├── orchestrator/
│   │   ├── agents/         # PlanningAgent, ReadAgent, WriteAgent, SynthesisAgent
│   │   ├── handlers/       # One handler per intent type
│   │   └── orchestrator.py # Three-phase pipeline coordinator
│   ├── context/            # Session store (Redis), profile loader
│   ├── tools/              # Tool definitions for agent function-calling
│   └── response_builder/   # Text + UI card assembly
│
├── balance/                # Balance pipeline (TASK-001)
│   ├── models.py           # SQLAlchemy ORM: PlatformConnection, Invoice, Transaction, JournalEntry
│   ├── google_client.py    # Google OAuth + Gmail REST API client
│   ├── gmail_service.py    # Pub/Sub push handling, invoice extraction
│   ├── basiq_service.py    # Basiq webhook handling, transaction ingestion
│   ├── connection_service.py # OAuth token management, platform connection lifecycle
│   ├── matching_engine.py  # Invoice ↔ transaction reconciliation algorithm
│   ├── journal_writer.py   # Double-entry journal entry writer
│   └── database.py         # SQLAlchemy engine + table creation
│
├── integrations/
│   ├── iaccount.py         # iAccount Java service client
│   ├── ibusiness.py        # iBusiness Java service client
│   ├── iuser.py            # iUser Java service client
│   └── platforms/
│       └── whatsapp/       # WhatsApp Cloud API adapter
│
├── services/
│   └── rag/                # RAG memory service (pgvector + OpenAI)
│
├── observability/          # Structured logging, OpenTelemetry tracing, Prometheus metrics
├── config.py               # Pydantic settings (reads from .env)
└── main.py                 # FastAPI app, lifespan startup/shutdown wiring
```

---

## Tests

```bash
# All tests
pytest

# Unit only
pytest tests/unit

# Integration only (no external services needed)
pytest tests/integration
```

Test layout mirrors source:

| Directory | Scope |
|---|---|
| `tests/unit/` | Pure logic — no DB, no network |
| `tests/integration/` | FastAPI endpoints via ASGITransport (mocked services) |
| `tests/e2e/` | Full pipeline smoke tests (skipped without live infra) |

---

## RAG memory

When `DATABASE_URL` is set, the service persists conversation context in PostgreSQL using pgvector embeddings. This allows the agent to recall prior interactions across sessions. Without it, the server starts normally and context is limited to the active Redis session.

---

## Observability

| Signal | Backend |
|---|---|
| Structured logs | `structlog` → JSON to stdout |
| Distributed traces | OpenTelemetry SDK |
| Metrics | Prometheus (`/metrics`) |
| Request IDs | Injected by `RequestIDMiddleware`, propagated in all log lines |
