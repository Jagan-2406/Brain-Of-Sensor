# Brain of Sensors (BoS) — Bug Fix + 3 New Features
### Target: Google Antigravity (agentic step-by-step execution)
### Depends on: Phases 1–6 complete, Target Detection add-on and Object Risk patch already applied

This document covers four separate work items, in order:
1. **Bug fix** — a photo/image of a person is being misclassified as a real person
2. **Feature 1** — dashboard UI overhaul: multi-page, filters, less "AI-generated" look
3. **Feature 2** — download last 7 days of data as PDF
4. **Feature 3** — alert sound triggered only on high-priority (red) events

Each section lists exactly which files may be touched. Do not modify any file outside what's listed in that section.

---

# PART 1 — Bug Fix: Photo of a Person Misidentified as a Real Person

## Problem

YOLOv8 detects "person" based on visual shape alone — it has no concept of whether it's looking at a real human or a flat photo/screen held up to the camera. A printed photo or phone screen showing a face currently gets logged and scored as object `"person"`, which is incorrect and inflates urgency scoring for something harmless.

## Root Cause

There is currently no "liveness" check anywhere in the pipeline — detection trusts YOLOv8's class label completely, with no secondary validation of whether the detected person is real.

## Fix Approach (lightweight, demo-appropriate)

Add a **secondary classification step** after YOLOv8 detects a "person," using two combined heuristics, run only on person detections (near-zero added cost for other object classes):

1. **Rectangular frame/edge check** — a held-up photo or phone screen almost always has a visible straight-edged rectangular boundary around or behind the face. Detect strong rectangular contours near the person bounding box; if found, this is a strong signal it's a photo/screen, not a real person.
2. **Micro-motion check** — sample the person's bounding box region across a few consecutive frames; a real person has small natural movement (breathing, minor head shifts, blinking); a static photo shows near-zero pixel variance over those frames.

If either heuristic strongly indicates a flat image, relabel the event's object as `"image"` instead of `"person"` before it is logged.

## Files allowed to be touched in this section
`main.py` (one new call site only), and a new file `liveness_check.py`. Do not modify `rules_engine.py` logic itself beyond adding one new entry to the existing `OBJECT_RISK_WEIGHT` table (Step 4 below) — no other change to that file.

---

### Step 1 — New Isolated Liveness Module

**Task for agent:**
1. Create `liveness_check.py`
2. Add a comment at the top: "Post-processing classifier run only on YOLOv8 'person' detections. Does not alter the YOLOv8 model or its other class outputs."

---

### Step 2 — Rectangular Frame Heuristic

**Task for agent:**
1. In `liveness_check.py`, write `has_rectangular_frame(frame, bbox) -> bool`:
   - Crop a region slightly larger than the given person bounding box
   - Run edge detection (OpenCV `Canny`) and contour detection on the cropped region
   - Check whether a strong, mostly-straight rectangular contour exists that roughly encloses or sits behind the face region (approximate using `cv2.approxPolyDP` to check for a 4-sided polygon with near-90-degree corners)
   - Return `True` if such a rectangle is found with reasonable confidence, else `False`

**Success check:** testing with a printed photo or phone held up to the camera returns `True`; testing with a real face in a normal room returns `False` in most cases.

---

### Step 3 — Micro-Motion Heuristic

**Task for agent:**
1. In `liveness_check.py`, write a small rolling buffer mechanism (e.g. a dict keyed by zone, storing the last 5 cropped face regions) and a function `has_natural_motion(zone, frame, bbox) -> bool`:
   - Crop the current bounding box region, add it to the zone's rolling buffer
   - Once at least 5 frames are buffered, compute pixel-difference variance across them
   - Return `True` if variance is above a defined minimum threshold (named constant, e.g. `MIN_MOTION_VARIANCE`), else `False`
   - If fewer than 5 frames are buffered yet, return `True` by default (assume real until proven otherwise, to avoid false "image" labeling on the very first frame)

**Success check:** a real person in frame shows variance above the threshold within a second or two; a static photo shows variance staying near zero.

---

### Step 4 — Combine Heuristics and Relabel

**Task for agent:**
1. In `liveness_check.py`, write `classify_person_detection(zone, frame, bbox) -> str`:
   - Calls both `has_rectangular_frame()` and `has_natural_motion()`
   - If `has_rectangular_frame()` is `True`, OR `has_natural_motion()` is `False` → return `"image"`
   - Otherwise → return `"person"`
2. In `main.py`, find the point where a YOLOv8 detection's class is read as `"person"` (this is in the existing Phase 1 event-construction logic). Add exactly one line immediately after that point:
   ```python
   if detected_class == "person":
       detected_class = liveness_check.classify_person_detection(zone, frame, bbox)
   ```
   Do not alter any other line in that function.
3. In `rules_engine.py`, add exactly one new entry to the existing `OBJECT_RISK_WEIGHT` table (do not alter any other entry or any other part of the file):
   ```python
   "image": 0.0,
   ```

**Success check:** holding up a printed photo or phone screen to the webcam now logs the event with `object = "image"` and scores `urgency = "low"`; a real person in frame continues to log correctly as `object = "person"` with normal scoring behavior.

---

### Step 5 — Verification

**Task for agent:**
1. Run three test cases back to back: (a) real person in frame, (b) printed photo of a face held up, (c) phone screen showing a face held up
2. Confirm (a) logs as `"person"` with normal scoring, and (b)/(c) log as `"image"` with `urgency = "low"`
3. Confirm no other existing behavior (Phases 1–6, target detection, object risk weighting for other classes) changed

**Bug fix completion checklist:**
- [ ] `liveness_check.py` created as an isolated module
- [ ] Rectangular frame and micro-motion heuristics both implemented and tested
- [ ] Person detections correctly relabeled to `"image"` when appropriate
- [ ] Only one line added to `main.py`, only one line added to `rules_engine.py`
- [ ] Real person detection behavior unchanged

---

# PART 2 — Feature 1: Dashboard UI Overhaul

## Objective

Replace the current single-page, plain live feed with a more complete, professionally designed multi-page dashboard — filters, better visual hierarchy, and a look that doesn't read as a bare-bones AI-generated page. This section touches Phase 6's frontend only.

## Files allowed to be touched
`app.py` (new routes only, do not remove existing `/api/events` route), `templates/` (new pages), new `static/` CSS/JS files. Do not touch backend scoring/tagging/summarization logic in any file.

---

### Step 1 — Define the Page Structure

**Task for agent:**
1. Plan four pages, each as its own template:
   - `dashboard.html` — main live feed (replaces/upgrades current `index.html`)
   - `history.html` — searchable/filterable table of past events
   - `analytics.html` — simple charts (event counts by zone, urgency distribution over the last 7 days)
   - `settings.html` — target detection controls (moved here from the main dashboard, keeping the live feed page focused)
2. Add a shared `base.html` template with a consistent header/navigation bar linking all four pages, and have each page extend it (Flask/Jinja `{% extends %}` pattern)

**Success check:** all four pages are reachable via the nav bar, share consistent header/styling, and each loads without errors (even with placeholder content at this stage).

---

### Step 2 — Visual Design Pass

**Task for agent:**
1. Create `static/dashboard.css` with a deliberate, cohesive design system (not default browser styling):
   - A defined color palette (e.g. dark background with accent colors for urgency levels — reuse the green/amber/red scheme already established in your pitch materials)
   - Consistent spacing, card-based layout for event entries, a readable type scale, and a proper header/nav bar styled distinctly from plain HTML defaults
2. Apply this stylesheet across all four pages via `base.html`
3. Avoid generic AI-tool defaults (no unstyled Bootstrap-blue buttons, no default system font) — define explicit font stacks and button/card styles

**Success check:** the dashboard visually reads as a designed product, not a default HTML scaffold — consistent across all four pages.

---

### Step 3 — Filters on the Live Feed and History Pages

**Task for agent:**
1. Add filter controls (dropdowns/checkboxes) for: zone, object type, urgency level, and a date range (history page only)
2. Implement filtering client-side (JavaScript) for the live feed (filtering the already-fetched event list), and server-side (query parameters on a new `/api/events/history` endpoint) for the history page, since that page may deal with much larger date ranges
3. Ensure filters combine correctly (e.g. "zone_1 AND high urgency" narrows to only matching events)

**Success check:** selecting filters on both pages correctly narrows the visible events, and clearing filters restores the full list.

---

### Step 4 — Analytics Page

**Task for agent:**
1. Add a new read-only endpoint `GET /api/analytics/summary` returning: event counts per zone (last 7 days), urgency level distribution (last 7 days), and object type breakdown
2. On `analytics.html`, render this as simple charts (a bar chart for zone counts, a pie/donut for urgency distribution) using a lightweight charting library (e.g. Chart.js via CDN)
3. Keep this page read-only — no event data is modified here

**Success check:** the analytics page loads real data from the last 7 days and renders readable charts that update correctly as new events accumulate.

---

### Step 5 — Verification

**Task for agent:**
1. Confirm the existing `/api/events` endpoint used by the live feed still works unchanged — no existing route behavior removed, only added to
2. Confirm navigation between all four pages works smoothly, filters function correctly, and the overall look is visually distinct from a default unstyled page

**Feature 1 completion checklist:**
- [ ] Four-page structure implemented with shared base template
- [ ] Deliberate visual design system applied consistently
- [ ] Filters working on live feed and history pages
- [ ] Analytics page rendering real 7-day data as charts
- [ ] No existing backend route or scoring/tagging logic modified

---

# PART 3 — Feature 2: Download Last 7 Days as PDF

## Objective

Add a button (on the history or dashboard page) that generates and downloads a PDF report of the last 7 days of event data.

## Files allowed to be touched
`app.py` (one new route), a new file `report_generator.py`, and an addition to whichever page the button lives on (from Part 2). No existing route or backend logic modified.

---

### Step 1 — PDF Generation Module

**Task for agent:**
1. Add a PDF library to `requirements.txt` (e.g. `reportlab` or `fpdf2`) and install it
2. Create `report_generator.py` with a function `generate_weekly_report() -> bytes`:
   - Queries the database for all events in the last 7 days
   - Builds a simple, readable PDF: a title, generation date, and a table with columns (timestamp, zone, object, urgency, summary_text)
   - Include a brief summary section at the top (total events, count by urgency level) before the detailed table
   - Return the PDF as in-memory bytes (do not require writing to disk first, though writing to a temp file and reading it back is acceptable if simpler)

**Success check:** calling `generate_weekly_report()` directly produces a valid, readable PDF file with correct data from the last 7 days.

---

### Step 2 — Download Route

**Task for agent:**
1. In `app.py`, add one new route `GET /api/report/weekly` that calls `generate_weekly_report()` and returns it as a downloadable file response (correct `Content-Type: application/pdf` and `Content-Disposition: attachment` headers)
2. This route must only read from the database — no writes

**Success check:** visiting this route in a browser (or clicking the button from Step 3) downloads a correctly formatted PDF file.

---

### Step 3 — UI Button

**Task for agent:**
1. Add a "Download Last 7 Days (PDF)" button to the history page (or dashboard page, whichever fits better from Part 2's layout)
2. The button simply links to or triggers a request to `/api/report/weekly` and lets the browser handle the download

**Success check:** clicking the button downloads the PDF without any page reload issues or broken links.

---

### Step 4 — Verification

**Task for agent:**
1. Confirm the generated PDF accurately reflects the actual last 7 days of data in the database (cross-check a few rows manually)
2. Confirm this feature doesn't affect any other route, page, or backend logic

**Feature 2 completion checklist:**
- [ ] `report_generator.py` produces an accurate, readable PDF
- [ ] Download route correctly serves the file with proper headers
- [ ] Button works from the UI without breaking existing pages
- [ ] No existing functionality affected

---

# PART 4 — Feature 3: Alert Sound for High-Priority (Red) Events Only

## Objective

Play a single alert sound in the browser whenever a new high-priority ("red") event appears on the live dashboard feed — so someone doesn't need to be staring at the screen to notice a critical alert.

## Files allowed to be touched
Only the live feed page's JavaScript (from Part 2's `dashboard.html` / its linked JS file) and one new static audio file. No backend files touched at all — this is a frontend-only feature.

---

### Step 1 — Add the Alert Sound Asset

**Task for agent:**
1. Add one short alert sound file (e.g. `alert.mp3`) to `static/sounds/`
2. Keep it short (1–2 seconds) and clearly audible but not jarring — a standard notification-style tone is appropriate

**Success check:** the audio file plays correctly when opened directly in a browser.

---

### Step 2 — Detect New High-Priority Events in the Polling Logic

**Task for agent:**
1. In the live feed's existing auto-refresh JavaScript (from Phase 6 / Part 2), maintain a simple in-memory set or list of event IDs already seen since the page loaded
2. On each poll cycle, compare newly fetched events against this seen-set
3. For any event that is both new (not previously seen) AND has `urgency === "high"`, mark it for an alert sound trigger
4. Add all newly fetched event IDs to the seen-set after processing, regardless of urgency

**Success check:** a simple console log confirms the detection logic correctly identifies only new high-priority events, not already-seen ones and not medium/low ones.

---

### Step 3 — Play the Sound

**Task for agent:**
1. Create a single reusable `Audio` object for the alert sound (avoid creating a new one on every play to prevent overlapping instances)
2. When Step 2 identifies one or more new high-priority events in a poll cycle, play the sound once per poll cycle (not once per event, to avoid a jarring burst of overlapping sounds if multiple high-priority events arrive simultaneously)

**Success check:** triggering a test high-priority event plays the sound exactly once; triggering multiple simultaneous high-priority events still plays it only once for that poll cycle; medium/low events never trigger it.

---

### Step 4 — Respect Browser Autoplay Restrictions

**Task for agent:**
1. Since browsers block unprompted audio autoplay, ensure the first sound playback is tied to a user interaction already present on the page (e.g. the first click anywhere on the dashboard, or a small one-time "Enable Alert Sound" button if no other interaction naturally occurs first)
2. Document this clearly with a code comment, since this is a browser platform constraint, not a bug

**Success check:** after the user has interacted with the page once (a click or the enable button), subsequent high-priority alerts play audio correctly without being blocked.

---

### Step 5 — Verification

**Task for agent:**
1. Confirm low/medium priority events never trigger sound
2. Confirm high-priority events trigger sound exactly once per occurrence (not repeating on every subsequent poll for the same already-alerted event)
3. Confirm this feature has zero effect on any backend file, route, or data — it is purely client-side

**Feature 3 completion checklist:**
- [ ] Alert sound asset added
- [ ] New high-priority events correctly detected via seen-set comparison
- [ ] Sound plays once per new high-priority occurrence, never for medium/low
- [ ] Autoplay restriction handled gracefully
- [ ] Zero backend files touched

---

# Final Combined Verification (run after all 4 parts are complete)

**Task for agent:**
1. Run the full system end to end: webcam detection → liveness-checked person/image classification → scoring → tagging → summarization → multi-page dashboard with filters → analytics → PDF export → alert sound on red events
2. Confirm every previously completed piece (Phases 1–6, target detection add-on, object risk patch) still behaves exactly as last verified
3. Confirm all four new work items function correctly together, with no interference between them

**This work is complete when all four completion checklists above are satisfied and the combined end-to-end run shows no regressions.**
