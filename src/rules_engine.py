import datetime
from database import get_zone_history

# --- Rule Threshold Constants ---
# Flags a burst of activity 3.0x or higher above the historical average for this zone/hour
HIGH_MULTIPLIER = 3.0

# Flags activity 1.5x above normal for this zone/hour
MEDIUM_MULTIPLIER = 1.5

# Low-traffic nighttime window: 9 PM (21:00) to 7 AM (07:00)
NIGHT_HOURS = set(list(range(21, 24)) + list(range(0, 7)))

# Baseline threshold (events/day) below which a nighttime hour is considered quiet
NIGHT_BASELINE_THRESHOLD = 0.5

# --- Object Risk Weight Table & Baseline Floor ---
# Assigns a relative risk weight per detected object class.
# This corrects for statistical rarity being mistaken for actual risk —
# e.g. a rarely-seen harmless object (like a phone) should not outscore
# a commonly-seen but security-relevant object (like a person).
# Values can be tuned later without changing the core scoring logic.
OBJECT_RISK_WEIGHT = {
    "person": 1.0,
    "vehicle": 1.0,
    "car": 1.0,
    "animal": 0.5,
    "backpack": 0.4,
    "pen": 0.1,
    "image": 0.05,
    "phone": 0.05,
    "chair": 0.0,
    "bottle": 0.0,
}
DEFAULT_RISK_WEIGHT = 0.1  # applied to any object class not explicitly listed

# Prevents runaway multipliers when an object's historical average is
# near zero (e.g. an object rarely or never seen before in this zone).
MIN_BASELINE = 0.1


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
        reason_codes = ["standard_object_detection"]

    return {
        "urgency": urgency,
        "reason_codes": reason_codes,
        "historical_average": round(historical_avg, 2),
        "live_count": live_count
    }
