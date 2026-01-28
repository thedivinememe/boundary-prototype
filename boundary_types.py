"""
Data structures for the boundary-based self-model.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from datetime import datetime


class BoundaryStatus(Enum):
    IDENTIFIED_CORE = "identified_core"
    IDENTIFIED_CONTINGENT = "identified_contingent"
    HELD = "held"
    OUTSIDE = "outside"
    UNCERTAIN = "uncertain"


class Provenance(Enum):
    TRAINING = "training"
    SYSTEM = "system"
    USER = "user"
    INFERENCE = "inference"
    IMPLICIT = "implicit"


@dataclass
class TestRecord:
    task: str
    outcome: str  # "success" or "failure"
    turn: int
    timestamp: str


@dataclass
class Boundary:
    domain: str
    status: BoundaryStatus
    rigidity: float  # 0.0 to 1.0
    rigidity_floor: Optional[float]  # Minimum rigidity, if protected
    confidence: float  # 0.0 to 1.0
    provenance: Provenance
    tested: bool
    test_history: list[TestRecord] = field(default_factory=list)
    derived_from: Optional[str] = None  # Parent boundary domain if split
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_interaction: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class BoundaryRevision:
    original_domain: str
    new_domains: list[str]
    trigger: str
    turn: int
    timestamp: str


@dataclass
class BoundaryMap:
    boundaries: dict[str, Boundary]  # domain -> Boundary
    revisions: list[BoundaryRevision]
    turn_count: int
