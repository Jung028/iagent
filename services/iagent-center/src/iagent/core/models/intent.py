# "dataclass" is a decorator that auto-generates __init__, __repr__, and __eq__
# based on the fields you declare. Similar to Java's @Data (Lombok) or records.
# Without it, you'd have to write the __init__ constructor manually.
from dataclasses import dataclass, field

# "StrEnum" is an enum where each value IS a string.
# In Java: public enum Intent { BALANCE_INQUIRY("balance_inquiry"), UNKNOWN("unknown"); }
# The difference: Python's StrEnum means the enum member itself behaves as a string,
# so Intent.BALANCE_INQUIRY == "balance_inquiry" is True.
from enum import StrEnum

# "Any" is a type hint meaning "any type is allowed here" — like Object in Java.
# We use it for the entities dict because entity values can be strings, numbers, etc.
from typing import Any


class Intent(StrEnum):
    # READ  — anything that queries data: balance, history, search, analysis, greetings, unknown
    READ     = "read"
    # WRITE — money movement, always requires confirmation
    TRANSFER = "transfer"
    TOP_UP   = "top_up"


# "@dataclass" is a decorator applied to the class below it.
# It reads the field declarations and auto-generates the __init__ method.
# Without it, you'd write: def __init__(self, intent, confidence, entities=None, cache_hit=False)
@dataclass
class IntentResult:
    """Holds the result of classifying a user's message.

    In Java this would be:
    public record IntentResult(Intent intent, double confidence,
                               Map<String, Object> entities, boolean cacheHit) {}
    """

    # Required fields (no default) — must be passed when creating an IntentResult.
    intent: Intent          # Which intent was detected
    confidence: float       # How confident the LLM was (0.0 to 1.0)

    # "field(default_factory=dict)" creates a NEW empty dict for each instance.
    # WHY not just "entities: dict = {}"? In Python, mutable default values (like dicts
    # and lists) are SHARED between all instances if you use them directly as defaults.
    # "default_factory=dict" tells Python to call dict() to create a fresh one each time.
    # This is a common Python gotcha that doesn't exist in Java (where you'd write "new HashMap<>()").
    entities: dict[str, Any] = field(default_factory=dict)

    # Simple boolean with a plain default. Safe to use directly because booleans are immutable.
    cache_hit: bool = False
