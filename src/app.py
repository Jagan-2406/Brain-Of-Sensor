"""
BoS Dashboard Backend Server (Flask)

Serves the Live Tactical Command UI and provides a read-only JSON API /api/events.
"""

import os
import sys
from flask import Flask, render_template, jsonify

# Add current directory to path so database imports work cleanly
sys.path.insert(0, os.path.dirname(__file__))

from database import SessionLocal, Event, init_db

app = Flask(__name__, template_folder=os.path.join(os.path.dirname(__file__), '..', 'templates'))

# Ensure database tables exist
init_db()


@app.route('/')
def index():
    """Renders the dashboard UI."""
    return render_template('index.html')


@app.route('/api/events', methods=['GET'])
def get_events():
    """
    API Endpoint: Returns recent 50 events formatted for the live dashboard feed.
    Read-only endpoint.
    """
    session = SessionLocal()
    try:
        # Retrieve recent 50 real and synthetic events ordered by timestamp descending
        events = session.query(Event).order_by(Event.id.desc()).limit(50).all()
        
        events_data = []
        for ev in events:
            # Parse reason_codes safely
            reason_codes_list = []
            if ev.reason_codes:
                if "," in ev.reason_codes:
                    reason_codes_list = [r.strip() for r in ev.reason_codes.split(",")]
                else:
                    reason_codes_list = [ev.reason_codes.strip()]

            # Default fallback summary if summary_text is empty
            summary = ev.summary_text
            if not summary:
                urg_str = ev.urgency or "low"
                summary = f"In {ev.zone}, a {ev.object} was detected with {urg_str} urgency."

            # Parse live_count from priority_tag_json if available
            live_count = 1
            if ev.priority_tag_json:
                try:
                    import json
                    tag_data = json.loads(ev.priority_tag_json)
                    live_count = tag_data.get("live_count", 1)
                except Exception:
                    pass

            events_data.append({
                "id": ev.id,
                "timestamp": ev.timestamp.isoformat() if ev.timestamp else "",
                "zone": ev.zone,
                "object": ev.object,
                "confidence": round(float(ev.confidence or 0.0), 2),
                "source": ev.source or "real",
                "urgency": (ev.urgency or "low").lower(),
                "reason_codes": reason_codes_list,
                "historical_avg": round(float(ev.historical_avg or 0.0), 2),
                "live_count": live_count,
                "priority_tag_json": ev.priority_tag_json,
                "summary_text": summary
            })

        return jsonify(events_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        session.close()


if __name__ == '__main__':
    print("Starting BoS Live Command Center Dashboard on http://127.0.0.1:5000 ...")
    app.run(host='127.0.0.1', port=5000, debug=True)
