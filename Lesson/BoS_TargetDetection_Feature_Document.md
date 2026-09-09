# Brain of Sensors (BoS) — Add-On Feature: Target Person Detection
### Scope: Isolated crowd-based target person identification, triggered by a UI toggle
### Target: Google Antigravity (agentic step-by-step execution)
### Depends on: Phases 1–6 fully complete and working
### Hard constraint: this feature must NOT modify the behavior, logic, or output of Phases 1–6 in any way when its toggle is OFF

---

## Feature Objective

Add a separate, independent capability: given 3 reference photos of specific people, let the user select one as the "target," and — only when explicitly enabled via a UI button — detect and visually highlight that specific person live on the webcam feed, even when other people are present in the same frame.

**Definition of done:**
- With the feature toggle OFF, the entire existing system (Phases 1–6) behaves exactly as it did before this feature was added — verified, not assumed.
- With the toggle ON and a target selected, the webcam feed visually highlights the correct person among multiple people in frame, distinctly from the normal YOLOv8 boxes used elsewhere in the system.
- No existing database table, schema, or file from Phases 1–6 is modified by this feature.

---

## Non-Negotiable Isolation Rules (read before starting)

1. Do not edit any existing scoring, tagging, or summarization logic (`rules_engine.py`, `priority_tag.py`, `summarizer.py`) at all.
2. Do not add columns to, or write into, the existing `events` table. Any data this feature needs to store must go into a brand-new, separate table.
3. Only one line of new code is allowed inside `main.py`'s existing capture loop — a single conditional check calling into the new isolated module. No other line in `main.py`'s existing Phase 1–6 logic may be changed.
4. All new logic lives in new, separate files. If unsure whether something belongs in an existing file, it does not — create a new file instead.

---

## Step 1 — New Isolated Module and Dependencies

**Task for agent:**
1. Add `face_recognition` and `dlib` to `requirements.txt`. Install both.
2. Create a new file `target_detection.py`. This file owns 100% of the new feature's logic.
3. At the top of the file, add a comment block stating clearly: "This module is fully isolated from the Phases 1–6 pipeline. It must never import from or write into rules_engine.py, priority_tag.py, summarizer.py, or the events table."

**Success check:** `pip list` confirms `face_recognition` and `dlib` installed without errors; `target_detection.py` exists as an empty-but-documented file.

---

## Step 2 — Reference Image Loading

**Task for agent:**
1. In `target_detection.py`, write `load_reference_faces(image_paths: list[str]) -> dict`:
   - Accepts exactly 3 file paths (the 3 friend photos)
   - For each image, load it and compute a face embedding using `face_recognition.face_encodings()`
   - Return a dictionary mapping a simple identifier (e.g. `"person_1"`, `"person_2"`, `"person_3"`) to its embedding vector
   - If a photo contains zero or more than one detected face, raise a clear error naming which file failed (reference photos must be single-face, clean shots)
2. Store the loaded embeddings dict in a module-level variable, e.g. `REFERENCE_FACES`, populated once at startup

**Success check:** loading 3 valid single-face photos returns a dict with 3 correctly shaped embeddings; loading a photo with no face or multiple faces raises a clear, specific error.

---

## Step 3 — Target Selection State

**Task for agent:**
1. In `target_detection.py`, add two module-level variables:
   - `target_mode_enabled: bool = False`
   - `selected_target_id: str | None = None`
2. Write `set_target(person_id: str)`:
   - Validates `person_id` exists in `REFERENCE_FACES`
   - Sets `selected_target_id` to it
   - Raises a clear error if an invalid `person_id` is passed
3. Write `toggle_target_mode(enabled: bool)`:
   - Sets `target_mode_enabled` directly to the given value

**Success check:** calling `set_target()` with a valid and then an invalid ID behaves correctly (success vs. clear error); `toggle_target_mode()` correctly flips the flag.

---

## Step 4 — Live Face Matching Logic

**Task for agent:**
1. In `target_detection.py`, write `match_target(frame) -> dict | None`:
   - If `target_mode_enabled` is `False` or `selected_target_id` is `None`, return `None` immediately (fast exit, no processing cost when inactive)
   - Otherwise: detect all faces in the given frame and compute their embeddings using `face_recognition`
   - Compare each detected face's embedding against `REFERENCE_FACES[selected_target_id]` using `face_recognition.compare_faces()` with a defined distance threshold (name this threshold as a constant at the top of the file, e.g. `MATCH_THRESHOLD = 0.6`, with a comment explaining it controls match strictness)
   - If a match is found, return its bounding box as `{"top": int, "right": int, "bottom": int, "left": int}`
   - If no match, return `None`
2. This function must only read the frame — it must never write to any database, file, or shared state outside this module

**Success check:** given a test frame containing the target among 2 other people, the function returns correct bounding box coordinates for the target only, and returns `None` for frames where the target isn't present.

---

## Step 5 — Optional Separate Logging Table

**Task for agent:**
1. In a new file `target_db.py` (do not add this to the existing `database.py`), define a brand-new table `target_matches` with columns: `id, timestamp, person_id, confidence`
2. Write `init_target_db()` to create this table if it doesn't exist, and `log_target_match(person_id, confidence)` to insert a row whenever `match_target()` succeeds
3. This table lives in the same SQLite file as `events` if convenient, but as a completely separate table with zero foreign keys or relationships to `events` — no schema coupling whatsoever

**Success check:** matches get logged into `target_matches` correctly, and the existing `events` table remains completely unaffected — verify by comparing its schema and row count before and after this feature is exercised.

---

## Step 6 — Minimal Hook Into the Main Loop

**Task for agent:**
1. Open `main.py`. Locate the point right after a frame is captured from the webcam, and right after (not inside) the existing Phase 1–5 detection/scoring/tagging/summarization chain runs on that frame.
2. Add exactly this conditional block, and nothing else, at that point:
   ```python
   import target_detection

   match = target_detection.match_target(frame)
   if match:
       draw_target_highlight(frame, match)  # defined in target_detection.py
   ```
3. In `target_detection.py`, implement `draw_target_highlight(frame, bbox)`:
   - Draws a bounding box visually distinct from the normal YOLOv8 boxes (e.g. thick colored border, different color, with a label like "TARGET")
4. Do not alter, reorder, wrap, or conditionally skip any existing line in `main.py` beyond adding this new block. The existing Phase 1–6 code must run exactly as before, in the same order, regardless of this addition.

**Success check:** with `target_mode_enabled = False` (default), running `main.py` produces byte-for-byte identical console output and database writes to a pre-feature baseline run. With it manually set to `True` and a target selected, the highlight appears correctly on the target's face when present in frame.

---

## Step 7 — Flask Endpoints (Isolated Routes)

**Task for agent:**
1. In `app.py` (from Phase 6), add three new routes. Do not modify any existing route in this file.
   - `POST /api/target/upload` — accepts 3 image uploads, saves them, calls `load_reference_faces()`, returns the 3 person IDs
   - `POST /api/target/select` — accepts a `person_id`, calls `set_target()`
   - `POST /api/target/toggle` — accepts `{"enabled": true/false}`, calls `toggle_target_mode()`
2. Each route should return a simple JSON success/error response
3. These routes must not import from or touch `rules_engine.py`, `priority_tag.py`, `summarizer.py`, or the `events` table logic in any way

**Success check:** each endpoint works correctly and independently via a manual test (e.g. `curl` or Postman), with no observable effect on the existing `/api/events` route or dashboard feed behavior.

---

## Step 8 — UI Additions (Additive Only)

**Task for agent:**
1. In `index.html` (Phase 6 dashboard), add new elements below or beside the existing event feed — do not restructure existing markup:
   - A file upload control for the 3 reference images
   - A dropdown or 3 buttons to select which uploaded person is the target
   - A single toggle button: "Target Detection: OFF" / "Target Detection: ON"
2. Add JavaScript that calls the three new endpoints from Step 7 on the appropriate interactions
3. Do not touch the existing polling/rendering logic for the event feed (Phase 6, Steps 3–6) — this is purely additive markup and script alongside it

**Success check:** the existing event feed continues to auto-refresh and render exactly as before; the new controls function correctly and independently alongside it on the same page.

---

## Step 9 — Full Isolation Verification (mandatory before calling this done)

**Task for agent:**
1. **Baseline run**: with the feature toggle OFF, run the complete system for a few minutes exactly as done at the end of Phase 6. Record: console output pattern, `events` table row count and schema, dashboard behavior.
2. **Feature run**: enable the toggle, select a target, and run again with the target person plus 2 others in frame together.
3. Compare:
   - `events` table schema and unrelated row data — must be identical in structure to baseline
   - Phase 1–6 console output/behavior when the toggle is off — must match baseline exactly
   - Only new behavior when toggle is on: the visual highlight on the correct person, and new rows appearing only in `target_matches`, never in `events`
4. Explicitly confirm: turning the feature off again (toggle OFF) returns the system to baseline behavior with no residual state affecting Phases 1–6.

**Success check:** two side-by-side verified runs (OFF and ON) proving zero interference in one direction and correct new functionality in the other.

---

## Feature Completion Checklist

- [ ] `target_detection.py` created as a fully self-contained module
- [ ] 3 reference images load correctly and produce valid face embeddings
- [ ] Target selection and toggle state work correctly and independently
- [ ] `match_target()` correctly identifies the selected person among multiple people in frame
- [ ] Matches logged only to the new, separate `target_matches` table — `events` untouched
- [ ] Exactly one new conditional block added to `main.py`, no existing lines altered
- [ ] New Flask routes added without modifying any existing route
- [ ] UI additions are purely additive; existing dashboard feed unaffected
- [ ] Verified: toggle OFF reproduces exact baseline Phase 1–6 behavior
- [ ] Verified: toggle ON correctly highlights the target person live, with no schema or logic bleed into the existing system

**This feature is complete and demo-ready when all boxes above are checked**, with both the OFF-state baseline match and the ON-state working highlight confirmed side by side.
