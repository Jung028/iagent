from typing import Any

from iagent.integrations.tracely import TracelyGraphClient

# Anthropic tool schema. The description is prescriptive about WHEN to call it,
# so the model reaches for graph traversal instead of guessing about architecture
# or scanning code/logs. Pass this in the `tools=[...]` list of a messages.create()
# call; when the model emits a `tool_use` block named "query_system_graph", run
# `handle(**block.input, graph_client=...)` and return the result as a tool_result.
DEFINITION: dict[str, Any] = {
    "name": "query_system_graph",
    "description": (
        "Answer system-level questions about the company's services, their dependencies, "
        "and the impact of a change by traversing the unified system graph (continuously "
        "built from code, runtime traces, and logs). Use this INSTEAD of guessing about "
        "architecture, reading source code, or searching logs. "
        "Call it to: resolve a service/table by name; see what a service calls or is called by; "
        "or compute the downstream blast radius of changing something. "
        "Operations: "
        "'find' = resolve a name (e.g. 'account service') to a canonical entity; "
        "'describe' = what an entity is plus its direct calls/callers and provenance; "
        "'neighbors' = one hop (who calls X, or what X calls); "
        "'blast_radius' = everything downstream that could be affected if X changes."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["find", "describe", "neighbors", "blast_radius"],
            },
            "query": {
                "type": "string",
                "description": (
                    "For 'find': a human name like 'account service' or 'transaction table'. "
                    "For the others: a canonical entity id like 'service:iaccount' "
                    "(call 'find' first if you don't have the id)."
                ),
            },
            "direction": {
                "type": "string",
                "enum": ["in", "out", "both"],
                "description": "For 'neighbors': 'in' = who calls X, 'out' = what X calls. Default 'both'.",
            },
            "depth": {
                "type": "integer",
                "description": "For 'blast_radius': max hops to traverse (1-6). Default 3.",
            },
        },
        "required": ["operation", "query"],
    },
}


async def handle(
    operation: str,
    query: str,
    graph_client: TracelyGraphClient,
    direction: str = "both",
    depth: int = 3,
    **ctx: str,  # request_id / user_id / etc. — forwarded as correlation headers
) -> dict[str, Any]:
    """Execute one graph traversal and return compact, pre-reconciled facts."""
    if operation == "find":
        return await graph_client.find(query, **ctx)
    if operation == "describe":
        return await graph_client.describe(query, **ctx)
    if operation == "neighbors":
        return await graph_client.neighbors(query, direction=direction, **ctx)
    if operation == "blast_radius":
        return await graph_client.blast_radius(query, depth=depth, **ctx)
    return {"error": f"unknown operation: {operation}"}
