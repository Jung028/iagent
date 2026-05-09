from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class ActionType(StrEnum):
    GREETING          = "greeting"
    READ_BALANCE      = "read_balance"
    READ_TRANSACTIONS = "read_transactions"
    WRITE_TRANSFER    = "write_transfer"
    WRITE_TOP_UP      = "write_top_up"


@dataclass
class PlanStep:
    action_type: ActionType
    description: str
    params: dict = field(default_factory=dict)

    @property
    def is_write(self) -> bool:
        return str(self.action_type).startswith("write_")

    @property
    def is_read(self) -> bool:
        return not self.is_write


@dataclass
class ExecutionPlan:
    steps: list[PlanStep]
    raw_intent: str = ""
