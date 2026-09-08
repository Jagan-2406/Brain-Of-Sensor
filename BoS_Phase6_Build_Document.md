# Brain of Sensors (BoS) — Phase 6 Build Document
### Scope: Dashboard — live, ranked, color-coded feed (final phase)
### Target: Google Antigravity (agentic step-by-step execution)
### Depends on: Phase 5 completed (`summary_text` + `priority_tag_json` persisted to DB)

---

## Phase 6 Objective

Build the final piece: a simple live dashboard that shows incoming events sorted by urgency, color-coded, displaying the plain-English summary from Phase 5. This is the piece judges/viewers actually watch during the demo — it should read cleanly and update in near real time as the webcam detects new events.

**Definition of done:** a browser page shows a live, auto-updating feed of events — newest and highest-urgency visually prioritized — each showing zone, object, urgency, and the generated summary sentence, with no manual refresh needed.

---

## Step 1 — Backend API Endpoint

**Task for agent:**
1. Add `flask` to `requirements.txt` if not already present, and install it
2. Create a new file `app.py`
3. Set up a minimal Flask app with one route: `GET /api/events`
   - Queries the database for the most recent N events (e.g. last 50), ordered by timestamp descending
   - For each event, return: `zone, object, timestamp, urgency, reason_codes, summary_text`
   - Return the result as JSON
4. Keep this endpoint read-only — it must not modify the database

**Success check:** running the Flask app and visiting `/api/events` in a browser (or via `curl`) returns a valid JSON array of recent events with all expected fields populated.

---

## Step 2 — Serve the Dashboard Page

**Task for agent:**
1. Create a `templates/` folder with an `index.html` file
2. Add a Flask route `GET /` that renders `index.html`
3. `index.html` should contain a basic page structure with:
   - A page title ("BoS — Live Incident Feed" or similar)
   - An empty container element (e.g. `<div id="event-feed"></div>`) where events will be rendered by JavaScript

**Success check:** visiting `/` in a browser shows a basic, empty page with the correct title and an empty feed container — confirms routing and templates are wired correctly.

---

## Step 3 — Fetch and Render Events

**Task for agent:**
1. In `index.html` (or a linked `static/dashboard.js` file), write JavaScript that:
   - Calls `GET /api/events` using `fetch()`
   - For each event returned, creates a card/row element showing: zone, object, timestamp, urgency label, and summary_text
   - Appends all event cards into the `#event-feed` container, most recent first
2. Keep the rendering logic simple — plain DOM manipulation is fine, no frontend framework needed for this MVP

**Success check:** reloading the page manually shows real event data rendered as readable cards, matching what's in the database.

---

## Step 4 — Color-Code by Urgency

**Task for agent:**
1. Add simple CSS classes for each urgency level: `.urgency-low`, `.urgency-medium`, `.urgency-high`
   - Low: neutral/gray background
   - Medium: amber/yellow background
   - High: red background
2. In the JavaScript rendering logic from Step 3, apply the correct class to each event card based on its `urgency` field
3. Ensure text remains clearly readable against each background color (sufficient contrast)

**Success check:** the rendered feed visually distinguishes urgency levels at a glance — a quick scan of the page should make high-priority events immediately stand out.

---

## Step 5 — Auto-Refresh

**Task for agent:**
1. Wrap the fetch-and-render logic from Step 3 in a function, and call it automatically on page load
2. Add a `setInterval()` that re-calls this function every few seconds (e.g. every 3–5 seconds) to poll for new events
3. When re-rendering, avoid a jarring full-page flicker — clear and rebuild the feed container cleanly on each poll (full rebuild is acceptable for MVP; no need for incremental diffing)

**Success check:** with the webcam running and detecting events in the background, the dashboard page updates on its own within a few seconds of a new event being logged — no manual refresh required.

---

## Step 6 — Sort by Priority, Then Recency

**Task for agent:**
1. Update the rendering logic so events are sorted with a two-level priority: urgency first (high → medium → low), then timestamp (most recent first) within each urgency group
2. This ensures the most important events are always visually at or near the top, not just the most recent ones

**Success check:** triggering a high-urgency test event while several low-urgency events are already showing causes the new high-urgency event to appear near the top of the feed, ahead of more recent but less urgent entries.

---

## Step 7 — Final End-to-End Verification

**Task for agent:**
1. Run the full system together: webcam detection (Phase 1) → scoring (Phase 3) → tagging (Phase 4) → summarization (Phase 5) → dashboard (Phase 6), all running simultaneously
2. Walk in front of the webcam at a normal time/pattern, then simulate an unusual pattern if possible (e.g. unusual zone, repeated triggers) and confirm both show up correctly on the dashboard — the normal one calm/low, the unusual one flagged and visually prioritized
3. Confirm the full loop timing is reasonable for a live demo — detection to dashboard update should feel like a few seconds, not a noticeable lag

**Success check:** the complete system runs live, end to end, with no manual steps between webcam detection and dashboard update — this is the exact loop to demo at the expo.

---

## Phase 6 Completion Checklist

- [ ] `/api/events` endpoint returns recent events as JSON
- [ ] Dashboard page loads and renders events as readable cards
- [ ] Urgency is color-coded clearly (low/medium/high)
- [ ] Feed auto-refreshes without manual reload
- [ ] Events are sorted by urgency first, then recency
- [ ] Full pipeline verified end to end, live, with acceptable demo timing

**All six phases complete.** BoS now runs as a full live loop: webcam detection → deterministic urgency scoring → structured priority tagging → LLM-generated plain-English summary → live, ranked, color-coded dashboard — ready for the expo demo.
