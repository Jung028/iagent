import functools
import time
from typing import Any, Callable

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter


def configure_tracing() -> None:
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    trace.set_tracer_provider(provider)


tracer = trace.get_tracer("iagent-center")


def trace_llm_call(stage: str) -> Callable[..., Any]:
    """Decorator that wraps an async LLM call with a trace span and latency metric."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            with tracer.start_as_current_span(f"llm.{stage}"):
                start = time.monotonic()
                result = await func(*args, **kwargs)
                elapsed = time.monotonic() - start
                from iagent.observability.metrics import llm_duration
                llm_duration.labels(model="claude-sonnet-4-5", stage=stage).observe(elapsed)
                return result

        return wrapper

    return decorator
