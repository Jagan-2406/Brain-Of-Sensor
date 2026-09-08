"""
PriorityTag Schema Module

This module defines the single, standardized contract (PriorityTag) consumed by:
1. LLM summarizer (Phase 5)
2. Interactive Dashboard (Phase 6)

Any future structural changes to PriorityTag must increment `schema_version`.
"""

import json
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any

VALID_URGENCIES = {"low", "medium", "high"}
CURRENT_SCHEMA_VERSION = "1.0"


@dataclass
class PriorityTag:
    zone: str
    object: str
    timestamp: str
    urgency: str
    confidence: float
    reason_codes: List[str] = field(default_factory=list)
    historical_avg: float = 0.0
    live_count: int = 0
    schema_version: str = CURRENT_SCHEMA_VERSION

    def to_dict(self) -> Dict[str, Any]:
        """Convert PriorityTag instance to a dictionary."""
        return asdict(self)

    def to_json(self) -> str:
        """Serialize PriorityTag instance to a JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PriorityTag":
        """Reconstruct PriorityTag instance from a dictionary."""
        return cls(
            zone=str(data.get("zone", "")),
            object=str(data.get("object", "")),
            timestamp=str(data.get("timestamp", "")),
            urgency=str(data.get("urgency", "")),
            confidence=float(data.get("confidence", 0.0)),
            reason_codes=list(data.get("reason_codes", [])),
            historical_avg=float(data.get("historical_avg", 0.0)),
            live_count=int(data.get("live_count", 0)),
            schema_version=str(data.get("schema_version", CURRENT_SCHEMA_VERSION)),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "PriorityTag":
        """Parse a JSON string back into a PriorityTag object."""
        data = json.loads(json_str)
        return cls.from_dict(data)


def build_priority_tag(event: Dict[str, Any], score_result: Dict[str, Any]) -> PriorityTag:
    """
    Assembles and validates a PriorityTag from a raw detection event and a score result.

    Args:
        event: Dictionary containing 'zone', 'object', 'timestamp', 'confidence'.
        score_result: Dictionary containing 'urgency', 'reason_codes',
                       'historical_avg' (or 'historical_average'), 'live_count'.

    Returns:
        PriorityTag instance.

    Raises:
        ValueError: If urgency is not strictly one of 'low', 'medium', 'high'.
    """
    urgency = str(score_result.get("urgency", "")).lower()
    if urgency not in VALID_URGENCIES:
        raise ValueError(
            f"Invalid urgency value '{urgency}'. Urgency must be strictly one of {VALID_URGENCIES}."
        )

    # Support either key name for historical average
    hist_avg = float(
        score_result.get("historical_avg", score_result.get("historical_average", 0.0))
    )

    tag = PriorityTag(
        zone=str(event.get("zone", "unknown_zone")),
        object=str(event.get("object", "person")),
        timestamp=str(event.get("timestamp", "")),
        urgency=urgency,
        confidence=round(float(event.get("confidence", 0.0)), 4),
        reason_codes=list(score_result.get("reason_codes", [])),
        historical_avg=round(hist_avg, 2),
        live_count=int(score_result.get("live_count", 1)),
        schema_version=CURRENT_SCHEMA_VERSION,
    )

    return tag
