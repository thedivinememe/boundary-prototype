"""
Core boundary management logic.
"""

from __future__ import annotations

import json
import os
from typing import Optional, Dict, List
from boundary_types import (
    Boundary, BoundaryMap, BoundaryStatus, Provenance,
    TestRecord, BoundaryRevision
)
from datetime import datetime

# Constants for rigidity updates
REINFORCEMENT_DELTA = 0.02
CONFLICT_DELTA = 0.03
DECAY_FACTOR = 0.995
CONFIDENCE_UNTESTED_CAP = 0.75
REFINEMENT_THRESHOLD = 0.4  # Confidence below this triggers refinement check
FAILURE_COUNT_FOR_REFINEMENT = 3


class BoundaryManager:
    def __init__(self, storage_path: str = None):
        # Determine the directory where this module lives
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        if storage_path is None:
            storage_path = os.path.join(self.base_dir, "boundaries.json")
        self.storage_path = storage_path
        self.boundary_map = self.load_or_initialize()

    def load_or_initialize(self) -> BoundaryMap:
        """Load existing boundaries or initialize from defaults."""
        try:
            with open(self.storage_path, 'r') as f:
                data = json.load(f)
                return self._deserialize(data)
        except FileNotFoundError:
            return self._load_initial_boundaries()

    def save(self):
        """Persist current boundary map."""
        with open(self.storage_path, 'w') as f:
            json.dump(self._serialize(), f, indent=2)

    def get_boundary(self, domain: str) -> Boundary | None:
        """Retrieve a boundary by domain."""
        return self.boundary_map.boundaries.get(domain)

    def get_all_boundaries(self) -> dict[str, Boundary]:
        """Get all boundaries."""
        return self.boundary_map.boundaries

    def record_outcome(self, domain: str, task: str, outcome: str):
        """
        Record a task outcome and update the relevant boundary.

        outcome: "success" or "failure"
        """
        boundary = self.get_boundary(domain)
        if not boundary:
            # Create new boundary if we encounter a new domain
            boundary = self._create_inferred_boundary(domain)
            self.boundary_map.boundaries[domain] = boundary

        # Record the test
        record = TestRecord(
            task=task[:100],  # Truncate for storage
            outcome=outcome,
            turn=self.boundary_map.turn_count,
            timestamp=datetime.now().isoformat()
        )
        boundary.test_history.append(record)
        boundary.tested = True
        boundary.last_interaction = datetime.now().isoformat()

        # Update confidence and rigidity
        if outcome == "success":
            self._on_success(boundary)
        elif outcome == "failure":
            self._on_failure(boundary)

        self.save()

        # Check if refinement is needed
        if self._should_refine(boundary):
            return {"needs_refinement": True, "boundary": boundary}

        return {"needs_refinement": False}

    def _on_success(self, boundary: Boundary):
        """Update boundary after successful task."""
        # Increase confidence
        boundary.confidence = min(1.0, boundary.confidence + REINFORCEMENT_DELTA)

        # Increase rigidity (but respect floor)
        boundary.rigidity = min(1.0, boundary.rigidity + REINFORCEMENT_DELTA)

        # If this was uncertain, it might move toward identified
        if boundary.status == BoundaryStatus.UNCERTAIN:
            if boundary.confidence > 0.7:
                boundary.status = BoundaryStatus.IDENTIFIED_CONTINGENT

    def _on_failure(self, boundary: Boundary):
        """Update boundary after failed task."""
        # Decrease confidence
        boundary.confidence = max(0.0, boundary.confidence - CONFLICT_DELTA)

        # Decrease rigidity (but respect floor)
        floor = boundary.rigidity_floor or 0.0
        new_rigidity = max(floor, boundary.rigidity - CONFLICT_DELTA)
        boundary.rigidity = new_rigidity

    def _should_refine(self, boundary: Boundary) -> bool:
        """Check if boundary should be refined (split)."""
        if boundary.confidence > REFINEMENT_THRESHOLD:
            return False

        # Count recent failures
        recent_failures = sum(
            1 for record in boundary.test_history[-10:]
            if record.outcome == "failure"
        )

        return recent_failures >= FAILURE_COUNT_FOR_REFINEMENT

    def refine_boundary(self, domain: str, new_boundaries: list[dict]):
        """
        Split a boundary into more specific sub-boundaries.

        new_boundaries: list of dicts with domain, status, confidence
        """
        old_boundary = self.get_boundary(domain)
        if not old_boundary:
            return

        # Archive the old boundary (mark as refined)
        del self.boundary_map.boundaries[domain]

        # Add new boundaries
        new_domains = []
        for nb in new_boundaries:
            # Handle invalid status values gracefully
            try:
                status = BoundaryStatus(nb["status"])
            except ValueError:
                # Map common invalid values to valid ones
                status_str = nb["status"].lower()
                if "outside" in status_str or "cannot" in status_str or "unable" in status_str:
                    status = BoundaryStatus.OUTSIDE
                elif "core" in status_str:
                    status = BoundaryStatus.IDENTIFIED_CORE
                elif "contingent" in status_str or "identified" in status_str:
                    status = BoundaryStatus.IDENTIFIED_CONTINGENT
                elif "held" in status_str:
                    status = BoundaryStatus.HELD
                else:
                    status = BoundaryStatus.UNCERTAIN

            new_boundary = Boundary(
                domain=nb["domain"],
                status=status,
                rigidity=old_boundary.rigidity * 0.8,  # Start lower
                rigidity_floor=None,
                confidence=nb.get("confidence", 0.5),
                provenance=Provenance.INFERENCE,
                tested=False,
                derived_from=domain
            )
            self.boundary_map.boundaries[nb["domain"]] = new_boundary
            new_domains.append(nb["domain"])

        # Record revision
        revision = BoundaryRevision(
            original_domain=domain,
            new_domains=new_domains,
            trigger="repeated_failure",
            turn=self.boundary_map.turn_count,
            timestamp=datetime.now().isoformat()
        )
        self.boundary_map.revisions.append(revision)

        self.save()

    def increment_turn(self):
        """Increment the turn counter."""
        self.boundary_map.turn_count += 1
        self.save()

    def get_summary_for_prompt(self) -> str:
        """Generate a summary of boundaries for the system prompt."""
        lines = []

        # Group by status
        by_status = {}
        for domain, boundary in self.boundary_map.boundaries.items():
            status = boundary.status.value
            if status not in by_status:
                by_status[status] = []
            by_status[status].append(boundary)

        # Format each group
        status_order = [
            "identified_core",
            "identified_contingent",
            "held",
            "uncertain",
            "outside"
        ]

        for status in status_order:
            if status in by_status:
                lines.append(f"\n{status.upper().replace('_', ' ')}:")
                for b in by_status[status]:
                    conf_str = f"(confidence: {b.confidence:.0%})"
                    tested_str = "[tested]" if b.tested else "[untested]"
                    lines.append(f"  - {b.domain} {conf_str} {tested_str}")

        # Add revision history if any
        if self.boundary_map.revisions:
            lines.append("\nSELF-MODEL REVISIONS:")
            for rev in self.boundary_map.revisions[-3:]:  # Last 3
                lines.append(
                    f"  - Split '{rev.original_domain}' into {rev.new_domains} "
                    f"(turn {rev.turn})"
                )

        return "\n".join(lines)

    def _create_inferred_boundary(self, domain: str) -> Boundary:
        """Create a new boundary when we encounter an unknown domain."""
        return Boundary(
            domain=domain,
            status=BoundaryStatus.UNCERTAIN,
            rigidity=0.5,
            rigidity_floor=None,
            confidence=0.5,
            provenance=Provenance.INFERENCE,
            tested=False
        )

    def _serialize(self) -> dict:
        """Convert boundary map to JSON-serializable dict."""
        return {
            "boundaries": {
                domain: {
                    "domain": b.domain,
                    "status": b.status.value,
                    "rigidity": b.rigidity,
                    "rigidity_floor": b.rigidity_floor,
                    "confidence": b.confidence,
                    "provenance": b.provenance.value,
                    "tested": b.tested,
                    "test_history": [
                        {"task": t.task, "outcome": t.outcome,
                         "turn": t.turn, "timestamp": t.timestamp}
                        for t in b.test_history
                    ],
                    "derived_from": b.derived_from,
                    "created_at": b.created_at,
                    "last_interaction": b.last_interaction
                }
                for domain, b in self.boundary_map.boundaries.items()
            },
            "revisions": [
                {
                    "original_domain": r.original_domain,
                    "new_domains": r.new_domains,
                    "trigger": r.trigger,
                    "turn": r.turn,
                    "timestamp": r.timestamp
                }
                for r in self.boundary_map.revisions
            ],
            "turn_count": self.boundary_map.turn_count
        }

    def _deserialize(self, data: dict) -> BoundaryMap:
        """Load boundary map from dict."""
        boundaries = {}
        for domain, b in data["boundaries"].items():
            boundaries[domain] = Boundary(
                domain=b["domain"],
                status=BoundaryStatus(b["status"]),
                rigidity=b["rigidity"],
                rigidity_floor=b.get("rigidity_floor"),
                confidence=b["confidence"],
                provenance=Provenance(b["provenance"]),
                tested=b["tested"],
                test_history=[
                    TestRecord(**t) for t in b.get("test_history", [])
                ],
                derived_from=b.get("derived_from"),
                created_at=b.get("created_at", datetime.now().isoformat()),
                last_interaction=b.get("last_interaction", datetime.now().isoformat())
            )

        revisions = [
            BoundaryRevision(**r) for r in data.get("revisions", [])
        ]

        return BoundaryMap(
            boundaries=boundaries,
            revisions=revisions,
            turn_count=data.get("turn_count", 0)
        )

    def _load_initial_boundaries(self) -> BoundaryMap:
        """Load initial boundary configuration."""
        initial_path = os.path.join(self.base_dir, "initial_boundaries.json")
        with open(initial_path, 'r') as f:
            data = json.load(f)
            return self._deserialize(data)
