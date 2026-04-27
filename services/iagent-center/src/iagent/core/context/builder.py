from datetime import date

from iagent.api.schemas.chat import ChatRequest
from iagent.core.models.intent import IntentResult
from iagent.core.context.models import AgentContext


class ContextBuilder:
    @staticmethod
    async def from_request(
        request: ChatRequest,
        intent_result: IntentResult,
        request_id: str,
        session_store: object | None = None,
        profile_loader: object | None = None,
        auth_token: str | None = None,
    ) -> AgentContext:
        """Build AgentContext from ChatRequest + IntentResult + request_id.

        session_store and profile_loader are optional — if None, history and
        user_profile are left as their defaults ([] and None). This keeps the
        builder functional before those services are wired up.
        """
        # session_id = user + calendar day → history resets each day naturally.
        # TODO: replace user_id prefix with JWT subject once AuthMiddleware is implemented.
        session_id = request.session_id or f"{request.user_id}:{date.today().isoformat()}"

        history = []
        if session_store is not None:
            history = await session_store.load(session_id)

        user_profile = None
        if profile_loader is not None:
            user_profile = await profile_loader.load(request.user_id)

        return AgentContext(
            user_id=request.user_id,
            request_id=request_id,
            session_id=session_id,
            auth_token=auth_token,
            raw_message=request.message,
            intent=intent_result.intent,
            confidence=intent_result.confidence,
            entities=intent_result.entities,
            history=history,
            user_profile=user_profile,
            platform_user_id=request.phone_no or "",
        )
