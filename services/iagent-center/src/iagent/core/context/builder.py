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
        memory_context: dict | None = None, 
    ) -> AgentContext:
        """Build AgentContext from ChatRequest + IntentResult + request_id.

        session_store and profile_loader are optional — if None, history and
        user_profile are left as their defaults ([] and None). This keeps the
        builder functional before those services are wired up.
        """
    
        # if the memory context is not null and is thread_id, then the session id is the thread id. 
        if memory_context and memory_context.get("thread_id"):
            session_id = memory_context["thread_id"]
        else : 
            session_id = request.session_id or f"{request.user_id}:{date.today().isoformat()}"

        if memory_context and memory_context.get("recent_messages"): 
            history = memory_context["recent_messages"]
        else: 
            history = []
            if session_store is not None:
                history = await session_store.load(session_id)

        # add an if the memory context is profile 
        if memory_context and memory_context.get("profile"):
            user_profile = memory_context.get["profile"]
        else: 
            user_profile = None
            if profile_loader is not None:
                user_profile = await profile_loader.load(request.user_id)

        # check merged entities, if there are past messages. 
        merged_entities = {}
        if memory_context and memory_context.get("entities"): 
            merged_entities.update(memory_context["entities"])
        merged_entities.update(intent_result.entities or {})


        return AgentContext(
            user_id=request.user_id,
            request_id=request_id,
            session_id=session_id,
            auth_token=auth_token,
            raw_message=request.message,
            intent=intent_result.intent,
            confidence=intent_result.confidence,
            entities=merged_entities,
            history=history,
            user_profile=user_profile,
            platform_user_id=request.phone_no or "",
        )
