"""
BoS Dashboard Backend Server (Flask)

Provides routes for multi-page command UI and read-only JSON & PDF API endpoints.
"""

import os
import sys
import datetime
import json
from flask import Flask, render_template, jsonify, request, Response

# Add current directory to path so database & report_generator imports work cleanly
sys.path.insert(0, os.path.dirname(__file__))

from database import SessionLocal, Event, init_db
from report_generator import generate_weekly_report

app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), '..', 'templates'),
    static_folder=os.path.join(os.path.dirname(__file__), '..', 'static')
)

# Ensure database tables exist
init_db()


# --- HTML Page Views ---

@app.route('/')
def index():
    """Main Live Feed View."""
    return render_template('dashboard.html')


@app.route('/history')
def history_page():
    """Searchable Historical Audit Log View."""
    return render_template('history.html')


@app.route('/analytics')
def analytics_page():
    """7-Day Analytics & Telemetry View."""
    return render_template('analytics.html')


# --- JSON API Endpoints ---

@app.route('/api/events', methods=['GET'])
def get_events():
    """
    API Endpoint: Returns recent 50 events formatted for the live feed.
    """
    session = SessionLocal()
    try:
        events = session.query(Event).order_by(Event.id.desc()).limit(50).all()
        events_data = [_format_event_dict(ev) for ev in events]
        return jsonify(events_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        session.close()


@app.route('/api/events/history', methods=['GET'])
def get_events_history():
    """
    API Endpoint: Returns filtered events for the Incident History page.
    Supports query params: zone, urgency, object, start_date, end_date.
    """
    zone_filter = request.args.get('zone', 'all').lower()
    urgency_filter = request.args.get('urgency', 'all').lower()
    object_filter = request.args.get('object', 'all').lower()

    session = SessionLocal()
    try:
        query = session.query(Event)

        if zone_filter != 'all':
            query = query.filter(Event.zone == zone_filter)
        if urgency_filter != 'all':
            query = query.filter(Event.urgency == urgency_filter)
        if object_filter != 'all':
            query = query.filter(Event.object == object_filter)

        events = query.order_by(Event.timestamp.desc()).limit(200).all()
        events_data = [_format_event_dict(ev) for ev in events]
        return jsonify(events_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        session.close()


@app.route('/api/analytics/summary', methods=['GET'])
def get_analytics_summary():
    """
    API Endpoint: Returns 7-day metric breakdowns for the Analytics page.
    """
    session = SessionLocal()
    try:
        cutoff = datetime.datetime.now() - datetime.timedelta(days=7)
        events = session.query(Event).filter(Event.timestamp >= cutoff).all()

        urgency_counts = {"high": 0, "medium": 0, "low": 0}
        zone_counts = {"Zone 1 (Left Field)": 0, "Zone 2 (Right Field)": 0}
        object_mapping = {
            "human": "Human",
            "person": "Human",
            "vehicle": "Vehicle",
            "car": "Vehicle",
            "animal": "Animal",
            "backpack": "Backpack",
            "cellphone": "Cellphone",
            "cell phone": "Cellphone",
            "chair": "Chair",
            "pen": "Pen",
            "image": "Photo / Image"
        }
        object_counts = {}

        # 7-day daily trend dict
        daily_trend = {}
        for d in range(6, -1, -1):
            day_str = (datetime.datetime.now() - datetime.timedelta(days=d)).strftime('%b %d')
            daily_trend[day_str] = 0

        conf_sum = 0.0
        conf_count = 0

        for ev in events:
            urg = (ev.urgency or "low").lower()
            if urg in urgency_counts:
                urgency_counts[urg] += 1

            z_raw = (ev.zone or "zone_1").lower()
            z_display = "Zone 1 (Left Field)" if "1" in z_raw else "Zone 2 (Right Field)"
            zone_counts[z_display] = zone_counts.get(z_display, 0) + 1

            raw_obj = (ev.object or "person").lower()
            obj_display = object_mapping.get(raw_obj, raw_obj.capitalize())
            object_counts[obj_display] = object_counts.get(obj_display, 0) + 1

            if ev.timestamp:
                day_key = ev.timestamp.strftime('%b %d')
                if day_key in daily_trend:
                    daily_trend[day_key] += 1

            if ev.confidence:
                conf_sum += float(ev.confidence)
                conf_count += 1

        total = len(events)
        high_pct = round((urgency_counts["high"] / total * 100), 1) if total > 0 else 0.0
        avg_conf = round((conf_sum / conf_count * 100), 1) if conf_count > 0 else 0.0
        top_zone = max(zone_counts, key=zone_counts.get) if zone_counts else "Zone 1 (Left Field)"

        return jsonify({
            "total_events": total,
            "high_urgency_pct": high_pct,
            "avg_confidence_pct": avg_conf,
            "top_active_zone": top_zone,
            "urgency_counts": urgency_counts,
            "zone_counts": zone_counts,
            "object_counts": object_counts,
            "daily_trend": daily_trend
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        session.close()


# --- Feature 2: PDF Report Download Endpoint ---

@app.route('/api/report/weekly', methods=['GET'])
def download_weekly_report():
    """
    API Endpoint: Generates and streams a downloadable 7-day PDF security report.
    """
    try:
        pdf_bytes = generate_weekly_report()
        response = Response(pdf_bytes, mimetype='application/pdf')
        filename = f"BoS_Weekly_Report_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    except Exception as e:
        return jsonify({"error": f"PDF Generation Error: {str(e)}"}), 500


# --- Helper Functions ---

def _format_event_dict(ev: Event) -> dict:
    reason_codes_list = []
    if ev.reason_codes:
        if "," in ev.reason_codes:
            reason_codes_list = [r.strip() for r in ev.reason_codes.split(",")]
        else:
            reason_codes_list = [ev.reason_codes.strip()]

    summary = ev.summary_text
    if not summary:
        urg_str = ev.urgency or "low"
        summary = f"In {ev.zone}, a {ev.object} was detected with {urg_str} urgency."

    live_count = 1
    if ev.priority_tag_json:
        try:
            tag_data = json.loads(ev.priority_tag_json)
            live_count = tag_data.get("live_count", 1)
        except Exception:
            pass

    return {
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
    }


if __name__ == '__main__':
    print("Starting BoS Live Command Center Dashboard on http://127.0.0.1:5000 ...")
    app.run(host='127.0.0.1', port=5000, debug=True)
