from prometheus_client import Counter, Histogram


def configure_metrics() -> None:
    pass


# HTTP
http_requests_total = Counter(
    "iagent_requests_total",
    "Total HTTP requests",
    ["endpoint", "method", "status_code"],
)

# Intent
intent_total = Counter(
    "iagent_intent_total",
    "Intent classifications",
    ["intent", "cache_hit"],
)

# LLM
llm_duration = Histogram(
    "iagent_llm_duration_seconds",
    "LLM call latency",
    ["model", "stage"],
)

# Backend
backend_requests_total = Counter(
    "iagent_backend_requests_total",
    "Backend service calls",
    ["service", "endpoint", "status"],
)
backend_duration = Histogram(
    "iagent_backend_duration_seconds",
    "Backend call latency",
    ["service", "endpoint"],
)
