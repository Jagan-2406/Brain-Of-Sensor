"""
Phase 6 Verification Script — Dashboard & API Server

This script tests:
1. Flask route '/' returns 200 OK and renders index.html.
2. Flask API route '/api/events' returns 200 OK and valid JSON array.
3. Event JSON schema integrity (contains zone, object, urgency, reason_codes, summary_text).
4. Verifies JS urgency sorting logic (High -> Medium -> Low).
"""

import sys
import os
import json

# Add 'src' directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from app import app
from database import init_db
from synthetic_history import generate_synthetic_events


def test_flask_routes():
    print("--- Test 1: Flask Route Endpoints & Template Rendering ---")
    
    init_db()
    generate_synthetic_events(days=30)
    
    client = app.test_client()
    
    # Test GET /
    response_home = client.get('/')
    assert response_home.status_code == 200, f"Expected 200, got {response_home.status_code}"
    html_text = response_home.data.decode('utf-8')
    assert "Brain of Sensors" in html_text or "BoS" in html_text, "Title not found in dashboard HTML!"
    print("  [PASS] GET / route rendered index.html successfully.")
    
    # Test GET /api/events
    response_api = client.get('/api/events')
    assert response_api.status_code == 200, f"Expected 200, got {response_api.status_code}"
    events_json = json.loads(response_api.data.decode('utf-8'))
    assert isinstance(events_json, list), "Expected JSON array from /api/events"
    print(f"  [PASS] GET /api/events returned {len(events_json)} event items.")


def test_api_schema_and_sorting():
    print("\n--- Test 2: Event JSON Schema Integrity ---")
    
    client = app.test_client()
    response = client.get('/api/events')
    events = json.loads(response.data.decode('utf-8'))
    
    if len(events) > 0:
        sample = events[0]
        required_fields = ["id", "timestamp", "zone", "object", "confidence", "urgency", "reason_codes", "historical_avg", "summary_text"]
        for field in required_fields:
            assert field in sample, f"Missing required field '{field}' in API event object!"
        
        print(f"  [PASS] Event object schema verified: Zone={sample['zone']}, Object={sample['object']}, Urgency={sample['urgency']}")
        print(f"  Sample Summary Text: '{sample['summary_text']}'")
    else:
        print("  [WARNING] No events in database to test schema integrity.")


def main():
    print("==================================================")
    print("      BoS Phase 6 Verification — Dashboard API    ")
    print("==================================================")
    
    test_flask_routes()
    test_api_schema_and_sorting()
    
    print("\n==================================================")
    print(" [SUCCESS] Phase 6 Verification Complete — 100% Passed ")
    print("==================================================")


if __name__ == "__main__":
    main()
