import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

from iagent.services.rag import rag_service as rag_module
from iagent.services.rag.repositories import InteractionRepository


def _make_service():
    session = MagicMock()
    factory = MagicMock()
    factory.return_value.__aenter__ = AsyncMock(return_value=session)
    factory.return_value.__aexit__ = AsyncMock(return_value=False)
    with patch.object(rag_module, "SentenceTransformer"):
        return rag_module.RAGService(factory, redis=MagicMock(), user_client=MagicMock())


def _interaction(role: str, message: str, result: dict) -> MagicMock:
    row = MagicMock()
    row.id = uuid.uuid4()
    row.role = role
    row.message = message
    row.result = result
    row.created_at = datetime.now(UTC)
    return row


async def test_get_thread_detail_returns_ui_card_as_result():
    """Assistant rows store the full ChatResponse envelope, but the API contract
    (FRONTEND_INTERFACES.md §4) says `result` is the UI card itself."""
    svc = _make_service()
    card = {"type": "balance_card", "accounts": [{"currency": "MYR", "balance": 10.0}]}
    envelope = {"intent": "read", "ui": card, "requires_action": False}
    rows = [
        _interaction("user", "What is my balance?", {}),
        _interaction("assistant", "", envelope),
    ]

    thread = MagicMock(summary="a summary")
    with (
        patch.object(rag_module, "ThreadRepository") as thread_repo,
        patch.object(rag_module, "InteractionRepository") as interaction_repo,
    ):
        thread_repo.return_value.query_by_thread_id = AsyncMock(return_value=thread)
        interaction_repo.return_value.query_all_by_thread = AsyncMock(return_value=rows)
        data = await svc.get_thread_detail(str(uuid.uuid4()))

    user_row, assistant_row = data["interactions"]
    assert user_row["result"] is None
    assert assistant_row["result"] == card


async def test_get_thread_detail_keeps_bare_result_for_legacy_rows():
    """Rows stored before the envelope existed (result is already the card) pass through."""
    svc = _make_service()
    card = {"type": "text_response", "message": "hi"}
    rows = [_interaction("assistant", "", card)]

    with (
        patch.object(rag_module, "ThreadRepository") as thread_repo,
        patch.object(rag_module, "InteractionRepository") as interaction_repo,
    ):
        thread_repo.return_value.query_by_thread_id = AsyncMock(return_value=MagicMock(summary=None))
        interaction_repo.return_value.query_all_by_thread = AsyncMock(return_value=rows)
        data = await svc.get_thread_detail(str(uuid.uuid4()))

    assert data["interactions"][0]["result"] == card


async def test_save_assistant_interaction_persists_message_text():
    """Assistant rows must carry a plain-text message so history renders even
    when the frontend only reads `message`."""
    session = MagicMock()
    repo = InteractionRepository(session)

    await repo.save_assistant_interaction(
        thread_id=uuid.uuid4(),
        user_id=1,
        result={"intent": "read", "ui": {"type": "text_response", "message": "Balance: MYR 10.00"}},
        message="Balance: MYR 10.00",
    )

    saved = session.add.call_args[0][0]
    assert saved.role == "assistant"
    assert saved.message == "Balance: MYR 10.00"
