# Brain of Sensors (BoS) — Phase 2 Build Document
### Scope: Storage & Historical Baseline (SQLite/Supabase + synthetic 30-day event history)
### Target: Google Antigravity (agentic step-by-step execution)
### Depends on: Phase 1 completed (`events.csv` producing live webcam events)

---

## Phase 2 Objective

Move events from a flat CSV into a proper database, and generate ~30 days of realistic synthetic historical events per zone so that Phase 3's rules engine has a baseline to compare live events against. No urgency scoring, no LLM, no dashboard yet — this phase is purely storage and historical data.

**Definition of done:** a database exists containing both real Phase 1 webcam events and synthetic historical events, all in one consistent schema, queryable by zone and time.

---

## Step 1 — Database Setup

**Task for agent:**
1. Inside `bos-phase1/` (continue in the same project, do not create a new folder), add `sqlalchemy` to `requirements.txt` and install it
2. Create a new file `database.py`
3. In `database.py`, define an `events` table with columns:
   ```
   id            (integer, primary key, autoincrement)
   timestamp     (datetime)
   zone          (text)
   object        (text)
   confidence    (float)
   source        (text — either "real" or "synthetic")
   ```
4. Use SQLite for local development: create a file `bos.db` in the project root
5. Write an `init_db()` function that creates the table if it doesn't already exist

**Success check:** running `init_db()` creates `bos.db` with an empty `events` table matching the schema above, with no errors on repeated runs.

---

## Step 2 — Migrate Phase 1 Logging to the Database

**Task for agent:**
1. Update `event_logger.py` so `log_event(event_dict)` now inserts into the `events` table (via `database.py`) instead of appending to `events.csv`
2. Every event logged from the live webcam in `main.py` should now include `"source": "real"` in its dictionary before being passed to `log_event()`
3. Keep `events.csv` writing as-is for now as a backup/debug trail — do not remove it, just add the database insert alongside it

**Success check:** running `main.py` and walking in front of the webcam produces new rows in `bos.db`'s `events` table with `source = "real"`, matching what's also being written to `events.csv`.

---

## Step 3 — Synthetic Historical Data Generator

**Task for agent:**
1. Create a new file `synthetic_history.py`
2. Write a function `generate_synthetic_events(days=30)` that creates realistic fake events for `zone_1` and `zone_2` covering the past 30 days, following these patterns:
   - **Daytime hours (e.g. 7 AM–9 PM):** higher frequency of "person" events (simulate normal foot traffic — e.g. several events per hour, randomized)
   - **Nighttime hours (e.g. 9 PM–7 AM):** much lower frequency (simulate a quiet period — e.g. 0–1 events per hour, randomized)
   - Occasionally include other object classes (e.g. "car") at a lower frequency than "person", if relevant to your zones
   - Randomize exact timestamps and counts within these bounds so the data looks natural, not perfectly uniform
3. Each generated event should have `"source": "synthetic"` set
4. Insert all generated events directly into the `events` table via `database.py`

**Success check:** running `generate_synthetic_events(30)` once populates `bos.db` with several hundred synthetic events spread realistically across the last 30 days, visibly showing higher counts in daytime hours and lower counts at night when queried.

---

## Step 4 — Query Helpers for Zone History

**Task for agent:**
1. In `database.py`, add a function `get_zone_history(zone, hour_of_day, lookback_days=30)` that:
   - Queries the `events` table for the given `zone`
   - Filters to events that occurred within the same `hour_of_day` window (e.g. events between 2 AM–3 AM, if checking the 2 AM hour) across the last `lookback_days`
   - Returns the count of matching events and their average count-per-occurrence
2. This function will be the core input for Phase 3's rules engine — it should return clean, simple numbers (e.g. "average of 0.3 events/hour for zone_1 at 2 AM over the last 30 days") that the next phase can compare live events against

**Success check:** calling `get_zone_history("zone_1", 2)` returns a low number (reflecting the quiet nighttime pattern from Step 3), and calling it for a daytime hour (e.g. `get_zone_history("zone_1", 14)`) returns a noticeably higher number — confirming the historical baseline data is queryable and realistic.

---

## Step 5 — Verification Pass

**Task for agent:**
1. Write a small standalone script `verify_phase2.py` that:
   - Prints the total row count in `events` table, split by `source` ("real" vs "synthetic")
   - Prints `get_zone_history()` results for both zones across a few sample hours (e.g. 2 AM, 10 AM, 6 PM)
2. Run this script and confirm the output makes sense (synthetic data dominates in volume, real data present from Phase 1 testing, historical averages reflect a believable day/night pattern)

**Success check:** `verify_phase2.py` output clearly shows a populated, realistic events table with a working zone-history query — ready to be consumed by Phase 3's rules engine.

---

## Phase 2 Completion Checklist

- [ ] `bos.db` created with correct `events` schema
- [ ] Live webcam events (Phase 1) now write into the database with `source = "real"`
- [ ] 30 days of synthetic historical events generated with `source = "synthetic"`, following realistic day/night patterns
- [ ] `get_zone_history()` returns sensible, queryable baseline numbers per zone and hour
- [ ] Verification script confirms the data looks correct end-to-end

**Phase 2 ends here.** Do not implement urgency scoring, priority tagging, LLM summarization, or the dashboard in this phase — those begin in Phase 3 onward, using `get_zone_history()` as the core input for the rules engine.
