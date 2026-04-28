import json

import structlog
from google import genai
from google.genai import types

log = structlog.get_logger(__name__)

_PLAN_PROMPT = """\
You are an intent planner for a financial AI assistant.
The user asked: "{question}"

Identify which financial analyses the user is requesting.
Return ONLY a JSON array of tasks. Each task has:
- "op": one of "count", "average", "total", "survival_forecast"
- "filter" (optional): {{"field": "amount", "lt": <number>}} or {{"field": "amount", "gt": <number>}}
- "field" (optional): which field to operate on, default "amount"

Examples:
"how many transactions below $1000?" → [{{"op":"count","filter":{{"field":"amount","lt":1000}}}}]
"what is my average spend and total?" → [{{"op":"average","field":"amount"}},{{"op":"total","field":"amount"}}]
"will I survive the week?" → [{{"op":"survival_forecast"}}]

Return ONLY a valid JSON array, no explanation.
"""

_FALLBACK_PLAN = [
    {"op": "count"},
    {"op": "average", "field": "amount"},
    {"op": "total", "field": "amount"},
]


class AnalysisPlanner:
    """Decomposes a free-text question into an ordered list of analysis tasks.

    This is the first stage of the RAG pipeline: before we touch any data,
    we ask the LLM what the user actually wants computed.
    """

    def __init__(self, client: genai.Client) -> None:
        self._client = client

    async def plan(self, question: str) -> list[dict]:
        try:
            # To save the model, we will use the fallback plan for now. 
            # response = await self._client.aio.models.generate_content(
            #     model="gemini-2.5-flash",
            #     contents=_PLAN_PROMPT.format(question=question),
            #     config=types.GenerateContentConfig(
            #         response_mime_type="application/json",
            #     ),
            # )
            response = []
            tasks = json.loads(response.text)
            if isinstance(tasks, list) and tasks:
                log.info("analysis_plan_built", task_count=len(tasks))
                return tasks
        except Exception as exc:
            log.warning("analysis_planner_failed", error=str(exc))

        log.info("analysis_plan_fallback")
        return _FALLBACK_PLAN
