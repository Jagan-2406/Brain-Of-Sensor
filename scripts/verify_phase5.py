"""
Phase 5 Verification Script — LLM Summarizer & Summary Validation

This script tests:
1. Prompt construction (`build_prompt`).
2. Deterministic fallback summary generator (`fallback_summarize`).
3. Output validation (`validate_summary` catches >40 word summaries and urgency contradictions).
4. Full integration with database persistence (`summary_text` column).
5. Prints recent real events formatted as: [urgency] summary_text
"""

import sys
import os
import datetime

# Add 'src' directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from priority_tag import PriorityTag, build_priority_tag
from rules_engine import score_event
from summarizer import build_prompt, fallback_summarize, summarize_event, validate_summary
from database import SessionLocal, Event, init_db
from event_logger import log_event
from synthetic_history import generate_synthetic_events


def test_prompt_and_fallback():
    print("--- Test 1: Prompt Construction & Fallback Generator ---")
    
    event = {
        "timestamp": datetime.datetime.now().isoformat(),
        "zone": "zone_1",
        "object": "person",
        "confidence": 0.91,
        "source": "real"
    }
    score_res = {
        "urgency": "high",
        "reason_codes": ["unusual_zone_frequency", "nighttime_activity"],
        "historical_average": 0.4,
        "live_count": 5
    }
    tag = build_priority_tag(event, score_res)
    
    prompt = build_prompt(tag)
    assert "Using only the data provided below" in prompt
    assert "zone_1" in prompt
    assert "high" in prompt
    print("  [PASS] Prompt built with strict constraints and correct tag data.")

    fallback_str = fallback_summarize(tag)
    assert "zone_1" in fallback_str
    assert "high urgency" in fallback_str
    assert "unusual_zone_frequency" in fallback_str
    print(f"  [PASS] Fallback Summary Generated: '{fallback_str}'")


def test_validation():
    print("\n--- Test 2: Summary Output Validation ---")
    
    event = {
        "timestamp": datetime.datetime.now().isoformat(),
        "zone": "zone_2",
        "object": "car",
        "confidence": 0.85,
        "source": "real"
    }
    score_res = {
        "urgency": "high",
        "reason_codes": ["unusual_zone_frequency"],
        "historical_average": 0.2,
        "live_count": 4
    }
    tag = build_priority_tag(event, score_res)
    
    # 1. Test valid summary
    valid_summary = "In zone_2, a car was detected with high urgency due to unusual zone frequency."
    result1 = validate_summary(valid_summary, tag)
    assert result1 == valid_summary
    print("  [PASS] Valid summary passed validation.")
    
    # 2. Test word length contradiction (> 40 words)
    long_summary = "word " * 45
    result2 = validate_summary(long_summary, tag)
    assert result2 == fallback_summarize(tag)
    print("  [PASS] Overly long summary (>40 words) correctly rejected, fallback used.")
    
    # 3. Test urgency contradiction (Tag says 'high', summary says 'low priority')
    contradictory_summary = "In zone_2, a car was detected with low priority near the entrance."
    result3 = validate_summary(contradictory_summary, tag)
    assert result3 == fallback_summarize(tag)
    print("  [PASS] Urgency contradiction ('low priority' vs 'high' tag) correctly rejected, fallback used.")


def test_database_persistence_and_query():
    print("\n--- Test 3: Database Persistence & Summary Log Inspection ---")
    
    init_db()
    generate_synthetic_events(days=30)
    
    now_dt = datetime.datetime.now()
    event_dict = {
        "timestamp": now_dt.isoformat(),
        "zone": "zone_1",
        "object": "person",
        "confidence": 0.94,
        "source": "real"
    }
    
    score_res = score_event(event_dict, live_count=12)
    priority_tag = build_priority_tag(event_dict, score_res)
    
    event_dict["urgency"] = score_res["urgency"]
    event_dict["reason_codes"] = score_res["reason_codes"]
    event_dict["historical_avg"] = score_res["historical_average"]
    event_dict["priority_tag_json"] = priority_tag.to_json()
    
    # Generate and validate summary
    raw_summary = summarize_event(priority_tag)
    validated_summary = validate_summary(raw_summary, priority_tag)
    event_dict["summary_text"] = validated_summary
    
    log_event(event_dict)
    
    session = SessionLocal()
    try:
        latest_event = session.query(Event).filter(
            Event.source == "real",
            Event.summary_text.isnot(None)
        ).order_by(Event.id.desc()).first()
        
        assert latest_event is not None, "Failed to retrieve real event with summary_text from database!"
        assert latest_event.summary_text == validated_summary
        print(f"  [PASS] Stored summary retrieved from database: '{latest_event.summary_text}'")

        # Print last 10 real events
        print("\n--- Recent Real Events Log ([urgency] summary_text) ---")
        real_events = session.query(Event).filter(
            Event.source == "real"
        ).order_by(Event.id.desc()).limit(10).all()
        
        for idx, ev in enumerate(real_events, 1):
            urg_str = (ev.urgency or 'LOW').upper()
            summary_disp = ev.summary_text or f"{ev.zone}: {ev.object} detected."
            print(f"  {idx:2d}. [{urg_str}] {summary_disp}")
            
    finally:
        session.close()


def main():
    print("==================================================")
    print("      BoS Phase 5 Verification — LLM Summarizer   ")
    print("==================================================")
    
    test_prompt_and_fallback()
    test_validation()
    test_database_persistence_and_query()
    
    print("\n==================================================")
    print(" [SUCCESS] Phase 5 Verification Complete — 100% Passed ")
    print("==================================================")


if __name__ == "__main__":
    main()
