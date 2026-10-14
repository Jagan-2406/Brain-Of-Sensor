import datetime
from database import get_zone_history



def score_event(event, live_count=1):
    """
    Computes a fixed, auditable urgency score for a live event based strictly on object category:
    - human & vehicle -> HIGH urgency
    - animal -> MEDIUM urgency
    - all other objects -> LOW urgency
    (No variance over time or frequency).
    """
    zone = event.get("zone", "zone_1")
    obj_class = (event.get("object", "human") or "human").lower()
    raw_timestamp = event.get("timestamp")

    if isinstance(raw_timestamp, datetime.datetime):
        event_dt = raw_timestamp
    elif isinstance(raw_timestamp, str):
        try:
            event_dt = datetime.datetime.fromisoformat(raw_timestamp)
        except ValueError:
            event_dt = datetime.datetime.now()
    else:
        event_dt = datetime.datetime.now()

    hour_of_day = event_dt.hour

    # Fetch 30-day historical baseline for tracking & reports
    _, historical_avg = get_zone_history(zone, hour_of_day, lookback_days=30)

    HIGH_CLASSES = ("human", "person", "vehicle", "car", "truck", "bus", "motorcycle", "bicycle")
    MEDIUM_CLASSES = ("animal", "dog", "cat", "bird", "horse", "sheep", "cow", "bear", "elephant")

    if obj_class in HIGH_CLASSES:
        urgency = "high"
        if obj_class in ("human", "person"):
            reason_codes = ["person_security_alert"]
        else:
            reason_codes = ["vehicle_security_alert"]
    elif obj_class in MEDIUM_CLASSES:
        urgency = "medium"
        reason_codes = ["animal_detection_alert"]
    else:
        urgency = "low"
        reason_codes = ["standard_object_detection", "low_risk_object_class"]

    return {
        "urgency": urgency,
        "reason_codes": reason_codes,
        "historical_average": round(historical_avg, 2),
        "live_count": live_count
    }
