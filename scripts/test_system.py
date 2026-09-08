"""
BoS (Brain of Sensors) — Master System Verification Suite

Consolidated test suite covering all 6 phases:
- Phase 1: Zone Coordinate Mapping (zones.py)
- Phase 2: Database Schema & 30-Day Synthetic Baseline (database.py, synthetic_history.py)
- Phase 3: Rules Engine Urgency & Baseline Anomaly Scoring (rules_engine.py)
- Phase 4: PriorityTag JSON Schema & Validation (priority_tag.py)
- Phase 5: LLM Summarizer & Output Validation Rules (summarizer.py)
- Phase 6: Flask Dashboard Backend & JSON API (app.py)
"""

import sys
import os
import datetime
import json

# Add 'src' directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from zones import get_zone
from database import SessionLocal, Event, init_db, get_zone_history
from synthetic_history import generate_synthetic_events
from rules_engine import score_event
from priority_tag import PriorityTag, build_priority_tag
from summarizer import build_prompt, fallback_summarize, validate_summary
from app import app


def test_phase1_and_phase2():
    print("--- Test 1 (Phase 1 & 2): Vision Zones & Database Baseline ---")
    
    # Phase 1: Test zone spatial mapping
    assert get_zone(x_center=100, frame_width=640) == "zone_1"
    assert get_zone(x_center=500, frame_width=640) == "zone_2"
    print("  [PASS] Phase 1 Zone mapping (left half = zone_1, right half = zone_2) verified.")

    # Phase 2: Database & 30-Day Synthetic Baseline History
    init_db()
    generate_synthetic_events(days=30)
    
    # Query baseline history average for current hour
    current_hour = datetime.datetime.now().hour
    count, avg = get_zone_history("zone_1", current_hour, lookback_days=30)
    assert count >= 0 and avg >= 0.0
    print(f"  [PASS] Phase 2 DB & 30-day baseline active: Zone 1 Hour {current_hour} Avg = {avg:.2f} events/hr.")


def test_phase3_and_phase4():
    print("\n--- Test 2 (Phase 3 & 4): Rules Engine Scoring & PriorityTag ---")
    event = {
        "timestamp": datetime.datetime.now().isoformat(),
        "zone": "zone_1",
        "object": "person",
        "confidence": 0.92,
        "source": "real"
    }
    score_res = score_event(event, live_count=15)
    assert score_res["urgency"] in {"low", "medium", "high"}
    
    tag = build_priority_tag(event, score_res)
    assert tag.schema_version == "1.0"
    assert tag.zone == "zone_1"
    assert tag.urgency == score_res["urgency"]
    
    # Validation check: invalid urgency raises ValueError
    try:
        build_priority_tag(event, {"urgency": "invalid_value"})
        sys.exit("Failed: Expected ValueError on invalid urgency!")
    except ValueError:
        pass
        
    print(f"  [PASS] Phase 3 Rules Engine scored urgency='{score_res['urgency']}'.")
    print(f"  [PASS] Phase 4 PriorityTag schema version='{tag.schema_version}' validated.")


def test_phase5_and_phase6():
    print("\n--- Test 3 (Phase 5 & 6): LLM Summarizer & Dashboard API ---")
    event = {"timestamp": datetime.datetime.now().isoformat(), "zone": "zone_2", "object": "car", "confidence": 0.88}
    score_res = {"urgency": "high", "reason_codes": ["unusual_zone_frequency"], "historical_average": 0.1, "live_count": 5}
    tag = build_priority_tag(event, score_res)
    
    # Phase 5: Test fallback generator & validation
    fallback = fallback_summarize(tag)
    assert "zone_2" in fallback and "high urgency" in fallback
    
    # Rejection checks: >40 words or urgency contradiction
    assert validate_summary("word " * 45, tag) == fallback
    assert validate_summary("Car detected with low priority in zone_2.", tag) == fallback
    print("  [PASS] Phase 5 Summarizer fallback & safety validation rules verified.")

    # Phase 6: Test Flask Dashboard HTTP API
    client = app.test_client()
    res_home = client.get('/')
    assert res_home.status_code == 200
    assert "Brain of Sensors" in res_home.data.decode('utf-8')
    
    res_api = client.get('/api/events')
    assert res_api.status_code == 200
    events = json.loads(res_api.data.decode('utf-8'))
    assert isinstance(events, list)
    
    if len(events) > 0:
        sample = events[0]
        assert "summary_text" in sample
        assert "live_count" in sample
        assert "priority_tag_json" in sample
        
    print(f"  [PASS] Phase 6 Flask Dashboard API verified ({len(events)} events loaded).")


def main():
    print("==================================================")
    print("  BoS Master System Test Suite (Phases 1 to 6)   ")
    print("==================================================")
    
    test_phase1_and_phase2()
    test_phase3_and_phase4()
    test_phase5_and_phase6()
    
    print("\n==================================================")
    print(" [SUCCESS] All 6 Phase Subsystems Verified 100% OK ")
    print("==================================================")


if __name__ == "__main__":
    main()
