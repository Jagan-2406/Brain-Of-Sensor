"""
Phase 4 Verification Script — Priority Tagging Schema & Persistence

This script tests:
1. PriorityTag dataclass creation, serialization, deserialization, and schema_version.
2. Constructor validation (invalid urgency raises ValueError).
3. Edge case: low urgency with empty reason_codes ([]).
4. Database column 'priority_tag_json' insertion, persistence, and deserialization.
"""

import sys
import os
import datetime
import json

# Add 'src' directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from priority_tag import PriorityTag, build_priority_tag
from rules_engine import score_event
from database import SessionLocal, Event, init_db
from event_logger import log_event
from synthetic_history import generate_synthetic_events

def test_schema_and_validation():
    print("--- Test 1: Schema & Constructor Validation ---")
    
    event = {
        "timestamp": datetime.datetime.now().isoformat(),
        "zone": "zone_1",
        "object": "person",
        "confidence": 0.88,
        "source": "real"
    }
    
    # Test valid urgencies
    for urgency in ["low", "medium", "high"]:
        score_res = {
            "urgency": urgency,
            "reason_codes": [f"TEST_{urgency.upper()}"],
            "historical_average": 5.2,
            "live_count": 8
        }
        tag = build_priority_tag(event, score_res)
        assert tag.urgency == urgency, f"Expected {urgency}, got {tag.urgency}"
        assert tag.schema_version == "1.0", f"Expected schema_version '1.0', got {tag.schema_version}"
        assert tag.confidence == 0.88
        assert tag.zone == "zone_1"
        assert tag.object == "person"
        
    print("  [PASS] Valid urgency tags built successfully.")

    # Test invalid urgency error
    try:
        invalid_score = {
            "urgency": "critical", # Not in {"low", "medium", "high"}
            "reason_codes": [],
            "historical_average": 1.0,
            "live_count": 1
        }
        build_priority_tag(event, invalid_score)
        print("  [FAIL] Expected ValueError for invalid urgency 'critical'!")
        sys.exit(1)
    except ValueError as e:
        print(f"  [PASS] Correctly caught invalid urgency error: {e}")


def test_edge_case_low_urgency():
    print("\n--- Test 2: Edge Case — Low Urgency with Empty Reason Codes ---")
    
    event = {
        "timestamp": datetime.datetime.now().isoformat(),
        "zone": "zone_2",
        "object": "person",
        "confidence": 0.95,
        "source": "real"
    }
    
    score_res = {
        "urgency": "low",
        "reason_codes": [], # No flags triggered
        "historical_average": 8.0,
        "live_count": 3
    }
    
    tag = build_priority_tag(event, score_res)
    assert tag.urgency == "low"
    assert tag.reason_codes == []
    
    # Test JSON serialization / deserialization roundtrip
    json_str = tag.to_json()
    reconstructed = PriorityTag.from_json(json_str)
    
    assert reconstructed.zone == "zone_2"
    assert reconstructed.urgency == "low"
    assert reconstructed.reason_codes == []
    assert reconstructed.schema_version == "1.0"
    
    print("  [PASS] Low urgency edge case built, serialized, and deserialized cleanly.")
    print(f"  Serialized JSON Payload: {json_str}")


def test_database_persistence():
    print("\n--- Test 3: Database Persistence & Query Verification ---")
    
    # Ensure tables exist and baseline history is generated
    init_db()
    generate_synthetic_events(days=30)
    
    now_dt = datetime.datetime.now()
    event_dict = {
        "timestamp": now_dt.isoformat(),
        "zone": "zone_1",
        "object": "person",
        "confidence": 0.92,
        "source": "real"
    }
    
    # Score event with rules engine
    score_res = score_event(event_dict, live_count=15)
    priority_tag = build_priority_tag(event_dict, score_res)
    
    event_dict["urgency"] = score_res["urgency"]
    event_dict["reason_codes"] = score_res["reason_codes"]
    event_dict["historical_avg"] = score_res["historical_average"]
    event_dict["priority_tag_json"] = priority_tag.to_json()
    
    # Log event to database
    log_event(event_dict)
    
    # Query database for recent real events
    session = SessionLocal()
    try:
        latest_event = session.query(Event).filter(
            Event.source == "real",
            Event.priority_tag_json.isnot(None)
        ).order_by(Event.id.desc()).first()
        
        assert latest_event is not None, "Failed to retrieve logged real event from DB!"
        assert latest_event.priority_tag_json is not None, "priority_tag_json column is NULL!"
        
        parsed_tag = PriorityTag.from_json(latest_event.priority_tag_json)
        
        assert parsed_tag.zone == "zone_1"
        assert parsed_tag.urgency == score_res["urgency"]
        assert parsed_tag.schema_version == "1.0"
        assert isinstance(parsed_tag.reason_codes, list)
        
        print(f"  [PASS] Successfully retrieved and parsed priority_tag_json from database (Event ID: {latest_event.id}).")
        print(f"  Db Column String: {latest_event.priority_tag_json}")
        print(f"  Parsed PriorityTag Object: {parsed_tag}")
    finally:
        session.close()


def main():
    print("==================================================")
    print("      BoS Phase 4 Verification — Priority Tagging ")
    print("==================================================")
    
    test_schema_and_validation()
    test_edge_case_low_urgency()
    test_database_persistence()
    
    print("\n==================================================")
    print(" [SUCCESS] Phase 4 Verification Complete — 100% Passed ")
    print("==================================================")

if __name__ == "__main__":
    main()
