# Brain of Sensors (BoS) — Phase 3 Build Document
### Scope: Rules / Stats Engine — deterministic urgency decision (no LLM, no priority tagging schema yet)
### Target: Google Antigravity (agentic step-by-step execution)
### Depends on: Phase 2 completed (`events` table + `get_zone_history()` working)

---

## Phase 3 Objective

Build the deterministic engine that decides how urgent a live event is, by comparing it against the historical baseline from Phase 2. No AI/LLM involved in this decision — every output must be traceable to a clear, explainable rule. No dashboard or LLM summary yet — this phase only produces the urgency decision itself.

**Definition of done:** given any live event, the system outputs an urgency level (`low` / `medium` / `high`) and a list of `reason_codes`, computed entirely from historical comparison logic — reproducible and explainable every time.

---

## Step 1 — Define the Scoring Rules

**Task for agent:**
1. Create a new file `rules_engine.py`
2. At the top of the file, define the rule thresholds as named constants (not magic numbers buried in logic), for example:
   ```
   HIGH_MULTIPLIER = 3.0      # live count vs historical average
   MEDIUM_MULTIPLIER = 1.5
   NIGHT_HOURS = range(21, 7)  # 9 PM–7 AM, treated as low-traffic window
   ```
3. Document each constant with a one-line comment explaining what real-world behavior it's meant to catch (e.g. "flags a burst of activity 3x above normal for this zone/hour")

**Success check:** `rules_engine.py` has clear, named, commented thresholds — no unexplained numbers anywhere in the scoring logic.

---

## Step 2 — Build the Core Scoring Function

**Task for agent:**
1. In `rules_engine.py`, write a function `score_event(event)` that:
   - Takes a live event dict: `{zone, object, count, timestamp}`
   - Calls `get_zone_history(zone, hour_of_day)` from Phase 2's `database.py` to get the historical average for that zone/hour
   - Compares the live event's count against the historical average using the thresholds from Step 1
   - Returns a result dict:
     ```
     {
       "urgency": "low" | "medium" | "high",
       "reason_codes": [...],
       "historical_average": <float>,
       "live_count": <int>
     }
     ```
2. Apply these rule checks, in order, and accumulate matching `reason_codes`:
   - If live count ≥ `HIGH_MULTIPLIER` × historical average → add `"unusual_zone_frequency"`, urgency at least `"high"`
   - Else if live count ≥ `MEDIUM_MULTIPLIER` × historical average → add `"unusual_zone_frequency"`, urgency at least `"medium"`
   - If the event's hour falls within `NIGHT_HOURS` and historical average for that hour is very low (e.g. below 0.5) → add `"unusual_time"`, bump urgency up one level if not already `"high"`
   - If none of the above trigger → urgency `"low"`, `reason_codes` empty or `["within_normal_pattern"]`

**Success check:** feeding `score_event()` a fabricated event that matches known synthetic daytime patterns returns `"low"`; feeding it an event with a high count at 2 AM (a quiet hour per Phase 2 data) returns `"high"` with both `unusual_time` and `unusual_zone_frequency` in `reason_codes`.

---

## Step 3 — Wire Live Detection Into the Scoring Engine

**Task for agent:**
1. In `main.py`, after an event is constructed and logged (Phase 1 + 2 logic), pass the same event dict into `score_event()` from `rules_engine.py`
2. Print the scoring result to the console alongside the event (for now — no storage of the score yet, that's Step 4)
3. Confirm this runs in real time without noticeably slowing down the webcam loop (the scoring function should be fast — it's just arithmetic and a DB query)

**Success check:** walking in front of the webcam prints both the raw event and its computed urgency/reason_codes live in the terminal, correctly reflecting whether that zone/time combination is historically normal or unusual.

---

## Step 4 — Persist Scores to the Database

**Task for agent:**
1. In `database.py`, extend the `events` table with three new columns:
   ```
   urgency        (text)
   reason_codes   (text — store as a comma-separated string or JSON string)
   historical_avg (float)
   ```
2. Update the event-insertion logic so that whenever a live event is logged (Phase 1/2 flow), its `score_event()` result is computed and stored in these new columns at the same time — do not insert the event first and update it later, do it in one insert
3. Synthetic historical events from Phase 2 do **not** need scores — leave those columns null/empty for `source = "synthetic"` rows

**Success check:** querying `bos.db` after a live test run shows real events (`source = "real"`) with populated `urgency`, `reason_codes`, and `historical_avg` columns, while synthetic rows remain unscored.

---

## Step 5 — Verification Pass

**Task for agent:**
1. Extend `verify_phase2.py` (or create `verify_phase3.py`) to:
   - Pull the last 10 real events from the database
   - Print each one's zone, object, count, urgency, and reason_codes in a readable table format
2. Manually walk through a few test scenarios in front of the webcam (normal daytime presence vs. simulating unusual timing/count if possible) and confirm the printed urgency levels match what you'd reasonably expect a human to flag

**Success check:** the verification output is human-readable and the urgency levels make intuitive sense given the historical patterns seeded in Phase 2 — every flagged result should be explainable by pointing at the specific rule that fired.

---

## Phase 3 Completion Checklist

- [ ] Rule thresholds defined as named, documented constants — no magic numbers
- [ ] `score_event()` correctly compares live events against Phase 2's historical baseline
- [ ] Urgency and reason_codes computed deterministically, with no AI/LLM involved
- [ ] Live webcam events are scored in real time without lag
- [ ] Scores are persisted to the database alongside each real event
- [ ] Verification confirms scoring behaves sensibly against known synthetic patterns

**Phase 3 ends here.** Do not implement the formal priority-tag schema, LLM summarization, or the dashboard in this phase — Phase 4 will take this raw `urgency` / `reason_codes` output and formalize it into a clean structured tag ready for the LLM and dashboard layers.
