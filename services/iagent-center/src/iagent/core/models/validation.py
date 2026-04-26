

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, List


class ValidationStatus(StrEnum):
    READY= "READY",
    INSUFICCIENT_CONTEXT="INSUFICCIENT_CONTEXT"

@dataclass
class ValidationResult:
    status: ValidationStatus 
    missing: List[str]
    cleaned_entities: dict[str, Any] | None = None
    question: str | None = None 
