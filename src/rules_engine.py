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
    "vehicle": 0.8,
    "car": 0.8,
    "backpack": 0.4,
    "cell phone": 0.05,
    "chair": 0.0,
    "bottle": 0.0,
}
DEFAULT_RISK_WEIGHT = 0.1  # applied to any object class not explicitly listed

# Prevents runaway multipliers when an object's historical average is
# near zero (e.g. an object rarely or never seen before in this zone).
MIN_BASELINE = 0.1


def score_event(event, live_count=1):
    """
    Computes a deterministic urgency score for a live event by comparing it
    against the 30-day historical baseline for the specified zone and hour.

    Parameters:
        event (dict): Event dictionary with keys 'zone', 'object', 'timestamp'.
        live_count (int): Number of detections in the current hour window.

    Returns:
        dict: {
            "urgency": "low" | "medium" | "high",
            "reason_codes": list of str,
            "historical_average": float,
            "live_count": int
        }
    """
    zone = event.get("zone", "zone_1")
    obj_class = event.get("object", "person")
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

    # Fetch 30-day historical baseline for this zone & hour
    _, historical_avg = get_zone_history(zone, hour_of_day, lookback_days=30)

    urgency = "low"
    reason_codes = []

    # Safe baseline floor to prevent divide-by-near-zero blowups
    safe_average = max(historical_avg, MIN_BASELINE)

    # Rule 1: Frequency Multipliers against historical average
    if live_count >= (HIGH_MULTIPLIER * safe_average):
        reason_codes.append("unusual_zone_frequency")
        urgency = "high"
    elif live_count >= (MEDIUM_MULTIPLIER * safe_average):
        reason_codes.append("unusual_zone_frequency")
        urgency = "medium"

    # Rule 2: Unusual Time Window (Nighttime check)
    if hour_of_day in NIGHT_HOURS and historical_avg < NIGHT_BASELINE_THRESHOLD:
        reason_codes.append("unusual_time")
        if urgency == "low":
            urgency = "medium"
        elif urgency == "medium":
            urgency = "high"

    # Rule 3: Object Risk Weighting Layer
    risk_weight = OBJECT_RISK_WEIGHT.get(obj_class, DEFAULT_RISK_WEIGHT)
    if risk_weight <= 0.1:
        urgency = "low"
        reason_codes.append("low_risk_object_class")

    # Rule 4: Default normal pattern
    if not reason_codes:
        urgency = "low"
        reason_codes = ["within_normal_pattern"]

    return {
        "urgency": urgency,
        "reason_codes": reason_codes,
        "historical_average": round(historical_avg, 2),
        "live_count": live_count
    }
