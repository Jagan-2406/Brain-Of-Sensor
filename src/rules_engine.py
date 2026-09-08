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

    # Rule 1: Frequency Multipliers against historical average
    # Avoid division by zero: if historical_avg is very small (e.g. 0), treat any event count >= 3 as high
    effective_avg = max(historical_avg, 0.1)

    if live_count >= (HIGH_MULTIPLIER * effective_avg):
        reason_codes.append("unusual_zone_frequency")
        urgency = "high"
    elif live_count >= (MEDIUM_MULTIPLIER * effective_avg):
        reason_codes.append("unusual_zone_frequency")
        urgency = "medium"

    # Rule 2: Unusual Time Window (Nighttime check)
    if hour_of_day in NIGHT_HOURS and historical_avg < NIGHT_BASELINE_THRESHOLD:
        reason_codes.append("unusual_time")
        if urgency == "low":
            urgency = "medium"
        elif urgency == "medium":
            urgency = "high"

    # Rule 3: Default normal pattern
    if not reason_codes:
        urgency = "low"
        reason_codes = ["within_normal_pattern"]

    return {
        "urgency": urgency,
        "reason_codes": reason_codes,
        "historical_average": round(historical_avg, 2),
        "live_count": live_count
    }
