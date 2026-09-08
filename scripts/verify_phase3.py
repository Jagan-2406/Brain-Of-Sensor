import sys
import os
import datetime

# Ensure src/ is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from database import init_db, SessionLocal, Event
from synthetic_history import generate_synthetic_events
from rules_engine import score_event

def run_verification():
    print("==================================================")
    print("          BoS Phase 3 Verification Pass           ")
    print("==================================================")

    # 1. Initialize DB & Generate Synthetic Baseline
    print("\n1. Initializing Database & 30-Day Historical Baseline...")
    init_db()
    generate_synthetic_events(30)

    session = SessionLocal()
    total_synth = session.query(Event).filter(Event.source == 'synthetic').count()
    total_real = session.query(Event).filter(Event.source == 'real').count()
    print(f"   Database contains {total_synth} synthetic events and {total_real} real events.")

    # 2. Test Rules Engine with Simulated Scenarios
    print("\n2. Testing Rules Engine Scoring Logic:")
    
    test_cases = [
        {
            "name": "Normal Daytime Event (14:00, 1 detection)",
            "event": {"zone": "zone_1", "object": "person", "timestamp": "2026-09-08T14:00:00"},
            "live_count": 1
        },
        {
            "name": "Daytime Spike / Frequency Burst (14:00, 30 detections)",
            "event": {"zone": "zone_1", "object": "person", "timestamp": "2026-09-08T14:00:00"},
            "live_count": 30
        },
        {
            "name": "Unusual Nighttime Activity (02:00, 1 detection)",
            "event": {"zone": "zone_1", "object": "person", "timestamp": "2026-09-08T02:00:00"},
            "live_count": 1
        },
        {
            "name": "Nighttime Burst Activity (02:00, 10 detections)",
            "event": {"zone": "zone_1", "object": "person", "timestamp": "2026-09-08T02:00:00"},
            "live_count": 10
        }
    ]

    for tc in test_cases:
        score = score_event(tc["event"], live_count=tc["live_count"])
        print(f"\n   Scenario: {tc['name']}")
        print(f"   --> Urgency: {score['urgency'].upper()}")
        print(f"   --> Reason Codes: {score['reason_codes']}")
        print(f"   --> Live Count: {score['live_count']} vs Historical Avg: {score['historical_average']}")

    # 3. Query Recent Real Events (if any exist)
    print("\n3. Querying Last 10 Real Webcam Events from Database:")
    real_events = (
        session.query(Event)
        .filter(Event.source == 'real')
        .order_by(Event.id.desc())
        .limit(10)
        .all()
    )

    if not real_events:
        print("   (No real events logged from live webcam feed yet.)")
    else:
        print(f"   {'ID':<5} | {'Timestamp':<20} | {'Zone':<8} | {'Object':<8} | {'Urgency':<8} | {'Historical Avg':<14} | {'Reasons'}")
        print("   " + "-" * 90)
        for ev in real_events:
            ts_str = ev.timestamp.strftime("%Y-%m-%d %H:%M:%S") if ev.timestamp else "N/A"
            reasons = ev.reason_codes if ev.reason_codes else "None"
            avg_str = f"{ev.historical_avg:.2f}" if ev.historical_avg is not None else "N/A"
            print(f"   {ev.id:<5} | {ts_str:<20} | {ev.zone:<8} | {ev.object:<8} | {str(ev.urgency).upper():<8} | {avg_str:<14} | {reasons}")

    session.close()
    print("\n==================================================")
    print("            Phase 3 Verification Complete!        ")
    print("==================================================")

if __name__ == "__main__":
    run_verification()
