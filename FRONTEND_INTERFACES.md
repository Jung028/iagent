# iAgent Frontend Interface Reference

---

## What to Build

**iAgent** is a conversational banking assistant — a desktop-first web app where users manage their finances by chatting in natural language. The mental model is WhatsApp crossed with a banking app: a chat thread is the primary surface, and the assistant responds with rich interactive cards instead of plain text.

### Product summary

- Users type messages like "What's my balance?", "Transfer RM 50 to Ali", or "Show me what I spent on food last month"
- The AI classifies intent and returns a structured UI card the frontend renders in the chat bubble
- Write operations (transfers, top-ups) require a two-step confirmation — the user sees a summary card, taps Confirm, then enters their PIN
- Users can also photograph a receipt and the AI extracts it into a bookkeeping entry
- Conversation history is grouped into threads (like WhatsApp chats) so users can pick up where they left off

### Target platform

Mobile-first web app. Design for a 390px wide phone screen first; desktop is a secondary constraint. Think of it as a Progressive Web App (PWA).

### App structure (pages & tabs)

The app has a **bottom tab bar** with three tabs:

```
┌──────────────────────────────┐
│         SCREEN AREA          │
│                              │
│                              │
│                              │
├──────────────────────────────┤
│  💬 Chat  │ 📄 Docs  │ 👤 Me │
└──────────────────────────────┘
```

| Tab | Label | What's on it |
|---|---|---|
| Tab 1 — Chat | **Chat** | Thread list + individual chat views |
| Tab 2 — Docs | **Documents** | Upload receipts, view extracted bookkeeping entries, run reconciliation |
| Tab 3 — Profile | **Me** | User profile, settings, log out |

#### Navigation flow within the Chat tab

```
Chat tab
  └── Thread List (default)
        └── [tap thread]  →  Chat View
        └── [new chat]    →  Chat View (empty)
                                └── [attachment icon]  →  Upload Sheet
                                                              └── [pick file]  →  stays in Chat View (card appears)
```

#### Navigation flow within the Docs tab

```
Docs tab
  └── Document List (uploaded receipts + extracted entries)
        └── [upload button]  →  File picker  →  POST /chat/upload  →  result shown inline
        └── [tap document]   →  Document Detail (extracted fields, reconciliation status)
              └── [reconcile button]  →  Reconciliation Result card
```

### Screens to build

#### 1. Thread list (home screen)
- Header: "iAgent" branding + new chat button
- Scrollable list of past conversation threads
- Each thread row: summary text, relative timestamp ("2 days ago"), unread indicator
- Tap → opens that thread's chat view
- Empty state: illustration + "Start your first conversation" prompt
- Data: `GET /threads?userId=<id>`

#### 2. Chat view
- Standard chat layout: bubbles on left (assistant) and right (user)
- User messages are plain text bubbles
- Assistant messages render a UI card (see Card Components below) instead of a plain bubble
- Input bar at bottom: text field + send button + attachment icon (opens file picker for receipt upload)
- Loading state: typing indicator (three animated dots) while awaiting AI response
- Thread title in nav bar; back button returns to thread list
- Data: `GET /threads/:id` to restore history, `POST /chat` to send messages

#### 3. Receipt upload flow
- Triggered from the attachment icon in the chat input bar
- Action picker sheet: "Bookkeeping" (extract receipt data) or "Ask a question about a document"
- File picker (image or PDF)
- Upload sends `POST /chat/upload`
- Result appears as a `bookkeeping_card` or `text_response` card in the chat

#### 4. Confirmation flow (for transfers)
- When the assistant returns a `confirmation_card`, render it with a prominent **Confirm** button and a **Cancel** button beneath the card
- Tapping Confirm resends the same message with `"confirmed": true`
- The assistant then returns a `pin_input_card`
- When the assistant returns a `pin_input_card`, render a 6-digit PIN input (dots, not numbers) inside the card
- PIN submission calls the Java backend directly (not `/chat`) using `transfer_token` and `account_id` from the card

#### 5. Settings / profile (minimal)
- User avatar + name
- Log out
- No other settings needed for MVP

### Card Components

Each assistant bubble renders one of these components. The `type` field decides which one.

| Card type | Component description |
|---|---|
| `balance_card` | Account balance tile(s): large currency + amount, small "as of" timestamp, pending amount in muted text. One tile per account. |
| `transaction_details_card` | Single transaction row: amount, type badge, timestamps. |
| `transaction_history_card` | Scrollable list of transaction rows inside the bubble. Show at most 10, with a "Show more" link. |
| `transaction_analysis_card` | Stats summary: total, average, count in a 3-column grid. Survival forecast in a highlighted banner. Summary text below. |
| `text_response` | Plain text paragraph inside a standard assistant bubble. No special chrome. |
| `structured_response` | Summary sentence at top; collapsible sections below with label/value rows or bullet points. |
| `confirmation_card` | Amber-tinted card with message text, a green **Confirm** button, and a grey **Cancel** button. |
| `pin_input_card` | 6-dot PIN entry inside a card. Tapping each dot fills it. Submit fires the transfer. |
| `bookkeeping_card` | Receipt form card: vendor, date, amount, currency, category dropdown. If `missing_fields` is non-empty, highlight those fields in red and show `clarifying_questions` text above the form. Confirm button saves the entry. |
| `error_card` | Red-tinted card with error message. If `recoverable: true`, show a **Try again** button. |

### Design direction

- **Palette:** Dark-mode first. Near-black background (`#0D0F14`), card surfaces at `#1A1D24`, primary accent a vivid teal (`#00C9B1`). Text: white at 100% for primary, 60% for secondary. Error red `#FF4D4D`.
- **Typography:** Inter for all UI text. Display numbers (balance amounts) in a mono font (JetBrains Mono or similar) so digits don't jump around.
- **Cards:** 12px border radius, subtle 1px border at 10% white opacity. No drop shadows — use the border instead.
- **Input bar:** Pinned to bottom, above the device home indicator safe area. Rounded pill shape.
- **Motion:** Message bubbles slide up + fade in. Card contents stagger in 50ms apart. Keep it fast — no animation over 200ms.
- **Chat bubble max-width:** 85% of screen width for user messages; cards stretch to 92% for readability.

### State management notes

- `session_id` is generated client-side (UUID v4) at the start of each conversation and sent with every `/chat` request in the same session
- `thread_id` comes back from the RAG service; store it after the first response and attach to all subsequent turns in the same thread
- The auth JWT is fetched at login and stored in memory (not localStorage) — attach to every request as `Authorization: Bearer <token>`
- In development mode the backend skips auth — useful for Lovable previews without a real auth flow

---

All endpoints served by the iAgent Center FastAPI backend at `http://localhost:8000`.

---

## Authentication

Every request (except `/health` and `/metrics`) requires:

```
Authorization: Bearer <jwt-token>
```

In development (`APP_ENV=development`) auth is skipped entirely — no token needed.

---

## 1. Chat — `POST /chat`

The core interaction loop. Send a user message, get back a UI card.

### Request

```json
{
  "user_id":   "user-abc-123",
  "message":   "What is my balance?",
  "phoneNo":   "+60123456789",
  "sessionId": "sess-xyz",
  "threadId":  "thread-001",
  "confirmed": false
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `user_id` | string | yes | Authenticated user ID |
| `message` | string | yes | 1–2000 chars |
| `phoneNo` | string | no | Used for WhatsApp continuity |
| `sessionId` | string | no | Redis session key for short-term history |
| `threadId` | string | no | RAG thread ID for long-term memory |
| `confirmed` | boolean | no | Set `true` when user taps Confirm on a `confirmation_card` |

### Response

```json
{
  "intent":          "read",
  "requires_action": false,
  "ui": { ... }
}
```

The `ui` field is one of the UI card types below, discriminated by the `type` field.

---

## 2. Chat Upload — `POST /chat/upload`

Upload a receipt, invoice, or document for bookkeeping or Q&A. Multipart form data.

### Request (multipart/form-data)

| Field | Type | Required | Notes |
|---|---|---|---|
| `user_id` | string | yes | |
| `action` | string | yes | `"bookkeeping"` or `"question"` |
| `message` | string | no | User's question (only for `action=question`) |
| `session_id` | string | no | |
| `file` | binary | yes | Image (PNG/JPEG/GIF/WEBP) or PDF |

### Response

Same `ChatResponse` shape as `POST /chat`. Returns either a `bookkeeping_card` or `text_response` card.

---

## 3. Thread List — `GET /threads?userId=<id>`

List all conversation threads for a user, most recently active first. Call on chatbot open to populate the sidebar.

### Request

| Query param | Required | Notes |
|---|---|---|
| `userId` | yes | |

### Response

```json
{
  "threads": [
    {
      "thread_id":   "thread-001",
      "summary":     "Balance check and transfer to Ali",
      "created_at":  "2026-06-01T10:00:00Z",
      "updated_at":  "2026-06-15T14:30:00Z"
    }
  ]
}
```

---

## 4. Thread Detail — `GET /threads/:thread_id`

Full ordered interaction history for a thread (oldest first). Use to restore a previous conversation.

### Response

```json
{
  "thread_id":    "thread-001",
  "summary":      "User asked about balance and initiated a transfer",
  "interactions": [
    {
      "id":         "int-001",
      "role":       "user",
      "message":    "What is my balance?",
      "result":     null,
      "created_at": "2026-06-01T10:00:00Z"
    },
    {
      "id":         "int-002",
      "role":       "assistant",
      "message":    null,
      "result":     { "type": "balance_card", ... },
      "created_at": "2026-06-01T10:00:01Z"
    }
  ]
}
```

---

## 5. Document Extract — `POST /api/v1/documents/extract`

Two-stage OCR + LLM pipeline. Converts a raw receipt or invoice (identified by URL) into structured bookkeeping fields.

### Request

```json
{
  "sourceDocumentId": "doc-001",
  "fileUrl":          "https://storage.example.com/receipts/doc-001.pdf",
  "mimeType":         "application/pdf",
  "metadata":         {}
}
```

Fields use camelCase in the wire format (alias-generated).

### Response

```json
{
  "source_document_id":  "doc-001",
  "status":              "success",
  "extracted": {
    "vendor":      "Mydin",
    "date":        "2026-06-28",
    "amount":      49.90,
    "currency":    "MYR",
    "category":    "GROCERIES",
    "description": "Weekly groceries",
    "items": [
      { "name": "Rice 5kg", "quantity": 1, "unit_price": 18.90 }
    ]
  },
  "missing_fields":        [],
  "clarifying_questions":  [],
  "raw_text":              null
}
```

| `status` value | Meaning |
|---|---|
| `"success"` | All fields extracted with confidence |
| `"partial"` | Some fields missing — check `missing_fields` and `clarifying_questions` |
| `"failed"` | Extraction failed entirely |

Valid `category` values: `GROCERIES`, `FOOD_DINING`, `TRANSPORT`, `FUEL`, `SHOPPING`, `ENTERTAINMENT`, `UTILITIES`, `RENT`, `HEALTHCARE`, `EDUCATION`, `TRANSFER`, `TOP_UP`, `OTHER`

---

## 6. Reconciliation Suggest — `POST /api/v1/reconciliation/suggest`

Given an extracted document and a list of candidate bank transactions, returns the best match with a confidence score.

### Request

```json
{
  "extracted_document": {
    "vendor_name":   "Mydin",
    "amount":        49.90,
    "currency":      "MYR",
    "invoice_date":  "2026-06-28",
    "raw_text":      null
  },
  "candidate_bank_transactions": [
    {
      "bank_transaction_id": "txn-99",
      "amount":              49.90,
      "currency":            "MYR",
      "transaction_date":    "2026-06-28",
      "description":         "MYDIN HOLDINGS",
      "counterparty_name":   "Mydin Holdings Bhd"
    }
  ]
}
```

### Response

```json
{
  "suggested_bank_transaction_id": "txn-99",
  "confidence_score":              0.97,
  "reason":                        "Amount, currency, and vendor name match exactly; date matches."
}
```

The service only suggests — it does not write anything. The frontend decides what to do based on `confidence_score`.

---

## 7. Health — `GET /health`

No auth required.

```json
{ "status": "ok", "db": true, "redis": true, "kafka": true, "anthropic_api": true }
```

---

## UI Card Reference

Every `ChatResponse.ui` is one of these shapes. Read the `type` field first, then render the appropriate component.

### `balance_card`

```json
{
  "type": "balance_card",
  "as_of": "2026-06-30T08:00:00Z",
  "accounts": [
    {
      "account_id": "acc-001",
      "currency":   "MYR",
      "balance":    1250.00,
      "pending":    50.00
    }
  ]
}
```

### `transaction_details_card`

```json
{
  "type": "transaction_details_card",
  "transaction_details": {
    "account_id":    "acc-001",
    "txn_id":        "txn-123",
    "amount":        50.00,
    "currency":      "MYR",
    "txn_type":      "TRANSFER",
    "created_at":    "2026-06-28T10:00:00Z",
    "completed_at":  "2026-06-28T10:00:05Z"
  }
}
```

### `transaction_history_card`

```json
{
  "type": "transaction_history_card",
  "transaction_history": [
    { "txn_id": "txn-1", "amount": 100.00, "currency": "MYR", ... }
  ]
}
```

### `transaction_analysis_card`

```json
{
  "type": "transaction_analysis_card",
  "analysis": {
    "count":               12,
    "average":             83.33,
    "total":               1000.00,
    "currency":            "MYR",
    "survival_forecast":   "Your balance covers ~18 days at current spend rate.",
    "summary":             "You spent RM 1,000 across 12 transactions this month."
  }
}
```

### `text_response`

Plain conversational answer.

```json
{
  "type":    "text_response",
  "message": "Yes, you sent RM 50.00 to Ali on 28 June 2026."
}
```

### `structured_response`

Multi-section rich answer with key-value rows or bullet points.

```json
{
  "type":    "structured_response",
  "summary": "Here is a breakdown of your recent spending:",
  "sections": [
    {
      "title": "Food & Dining",
      "items": [
        { "label": "Total",   "value": "RM 320.00" },
        { "label": "Count",   "value": "8 transactions" },
        { "text": null }
      ]
    }
  ]
}
```

A `ResponseItem` is either a key-value row (`label` + `value`) or a plain bullet (`text`).

### `confirmation_card`

Shown before any write operation (transfer, top-up). The frontend must display a Confirm button.

```json
{
  "type":    "confirmation_card",
  "message": "Confirm transfer of RM 50.00 to Ali?",
  "action":  "write_transfer"
}
```

**Frontend action:** render a Confirm button. When tapped, resend the original `POST /chat` with `"confirmed": true`.

### `pin_input_card`

Shown after the user confirms. The frontend must collect the user's PIN and call `transferConfirm` directly (not via `/chat`).

```json
{
  "type":           "pin_input_card",
  "message":        "Enter your 6-digit PIN to authorise the transfer.",
  "action":         "write_transfer",
  "transfer_token": "<opaque-token-from-transferInit>",
  "account_id":     "acc-001"
}
```

**Frontend action:** show a PIN input. Pass `transfer_token` and `account_id` directly to the `transferConfirm` Java backend endpoint.

### `bookkeeping_card`

Returned from `POST /chat/upload` with `action=bookkeeping`.

```json
{
  "type": "bookkeeping_card",
  "message": "I extracted the following entry. Please confirm to add it.",
  "entry": {
    "vendor":      "Mydin",
    "date":        "2026-06-28",
    "amount":      49.90,
    "currency":    "MYR",
    "category":    "GROCERIES",
    "description": "Weekly groceries"
  },
  "missing_fields":       ["amount"],
  "clarifying_questions": ["What was the total amount on the receipt?"]
}
```

When `missing_fields` is non-empty, prompt the user with `clarifying_questions` before saving.

### `error_card`

```json
{
  "type":        "error_card",
  "code":        "service_unavailable",
  "message":     "Balance service is temporarily unavailable. Please try again.",
  "recoverable": true
}
```

| `recoverable` | Meaning |
|---|---|
| `true` | Show a retry button |
| `false` | Show a contact-support message |

---

## Interaction Flows

### Balance inquiry

```
User: "What's my balance?"
  → POST /chat { message: "What's my balance?", user_id, sessionId }
  ← ChatResponse { intent: "read", ui: { type: "balance_card", ... } }
```

### Transfer (two-turn confirmation)

```
Turn 1 — user initiates:
  → POST /chat { message: "Transfer RM 50 to Ali", confirmed: false }
  ← ChatResponse { ui: { type: "confirmation_card", message: "Confirm transfer of RM 50 to Ali?" } }

Turn 2 — user confirms:
  → POST /chat { message: "Transfer RM 50 to Ali", confirmed: true }
  ← ChatResponse { ui: { type: "pin_input_card", transfer_token: "...", account_id: "..." } }

Turn 3 — frontend calls Java backend directly (not /chat):
  → POST <iaccount>/transferConfirm { transfer_token, account_id, pin }
  ← transfer result
```

### Document bookkeeping upload

```
→ POST /chat/upload (multipart) { user_id, action: "bookkeeping", file: <receipt> }
← ChatResponse { ui: { type: "bookkeeping_card", entry: {...}, missing_fields: [...] } }

If missing_fields is non-empty:
  → display clarifying_questions to user, collect answers
  → POST /chat { message: "<user's answers>" }

If confirmed:
  → save the bookkeeping entry via your own storage API
```

### Reconciliation flow

```
Step 1 — extract the document:
  → POST /api/v1/documents/extract { sourceDocumentId, fileUrl, mimeType }
  ← DocumentExtractResponse { extracted: { vendor, amount, ... } }

Step 2 — fetch candidate bank transactions from iAccount (Java backend directly)

Step 3 — ask AI to match:
  → POST /api/v1/reconciliation/suggest { extracted_document, candidate_bank_transactions }
  ← ReconciliationSuggestion { suggested_bank_transaction_id, confidence_score, reason }

Step 4 — if confidence_score >= 0.85, auto-reconcile; else ask user to confirm
```

---

## Intent Types

The `intent` field in `ChatResponse` tells the frontend what the AI understood.

| Intent value | Description |
|---|---|
| `"read"` | Balance inquiry, transaction history, analysis, Q&A, greetings |
| `"transfer"` | Fund transfer between accounts |
| `"top_up"` | Account top-up / reload |
| `"bookkeeping_entry"` | Receipt uploaded and parsed |
| `"document_question"` | File uploaded with a question |
| `"error"` | Processing failed |

---

## Error Handling

| HTTP status | Meaning |
|---|---|
| `200` | Success (even partial — check `ui.type === "error_card"`) |
| `401` | Missing or invalid `Authorization` header |
| `422` | Request validation failed (e.g. message too long, missing required field) |
| `503` | Downstream service unavailable |

Application-level errors are returned as `200` responses with `ui.type === "error_card"`. Always check `ui.type` before rendering.
