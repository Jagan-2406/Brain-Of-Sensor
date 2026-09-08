# Brain of Sensors (BoS) — Phase 4 Build Document
### Scope: Priority Tagging — formalize the rules-engine output into a clean structured schema
### Target: Google Antigravity (agentic step-by-step execution)
### Depends on: Phase 3 completed (`score_event()` producing urgency + reason_codes, persisted to DB)

---

## Phase 4 Objective

Phase 3 already computes urgency and reason_codes correctly, but the output is loose (a raw dict, informally shaped). Phase 4 formalizes this into a single, consistent, versioned "priority tag" schema — the exact structured payload that Phase 5 (LLM) and Phase 6 (dashboard) will both consume. No new scoring logic is introduced here — this phase is about shaping and standardizing the output, not changing how urgency is decided.

**Definition of done:** every scored event produces one clean, predictable `priority_tag` object, stored in the database in a single column, ready to be handed to an LLM prompt or rendered directly in a UI without further transformation.

---

## Step 1 — Define the Priority Tag Schema

**Task for agent:**
1. Create a new file `priority_tag.py`
2. Define the formal schema as a Python dataclass or typed dict, named `PriorityTag`, with these fields:
   ```
   zone            (str)
   object          (str)
   timestamp       (str, ISO format)
   urgency         (str — one of "low", "medium", "high")
   confidence      (float — detection confidence from YOLOv8, carried through from Phase 1)
   reason_codes    (list of str — from Phase 3)
   historical_avg  (float — from Phase 3)
   live_count      (int — from Phase 3)
   schema_version  (str — hardcode "1.0" for now)
   ```
3. Add a short docstring explaining that this is the single contract consumed by both the LLM summarizer (Phase 5) and the dashboard (Phase 6) — any future field changes must update `schema_version`

**Success check:** `PriorityTag` is a clearly defined, typed structure — not a loose dict — that fully describes one scored event.

---

## Step 2 — Build the Tag Constructor

**Task for agent:**
1. In `priority_tag.py`, write a function `build_priority_tag(event, score_result)` that:
   - Takes the original event dict (from Phase 1/2: zone, object, timestamp, confidence) and the score result dict (from Phase 3: urgency, reason_codes, historical_average, live_count)
   - Combines them into a single `PriorityTag` instance, filling every field correctly
   - Validates that `urgency` is strictly one of `"low"`, `"medium"`, `"high"` — raise a clear error if not (this guards against any future rule change in Phase 3 producing an unexpected value)
2. This function should not recompute or alter urgency in any way — it only assembles and validates what Phase 3 already decided

**Success check:** calling `build_priority_tag()` with a sample event and score result returns a correctly populated `PriorityTag`, and passing a malformed urgency value raises a clear validation error rather than silently proceeding.

---

## Step 3 — Wire Into the Live Pipeline

**Task for agent:**
1. In `main.py`, after `score_event()` runs (Phase 3 step), call `build_priority_tag()` with the event and score result to produce the `PriorityTag`
2. Print the resulting `PriorityTag` to the console in a clean, readable format for verification during this phase

**Success check:** walking in front of the webcam now prints a fully formed, consistent priority tag for every detected event, not just loose urgency/reason_code output.

---

## Step 4 — Persist the Tag as Structured Data

**Task for agent:**
1. In `database.py`, add one new column to the `events` table: `priority_tag_json` (text) — this stores the entire `PriorityTag` serialized as a JSON string
2. Update the event-insertion logic so that, alongside the existing individual columns (urgency, reason_codes, etc. from Phase 3), the full serialized `PriorityTag` is also stored in this new column
3. Keep the individual Phase 3 columns as-is for now — do not remove them, since they're still useful for direct SQL querying; `priority_tag_json` is the consolidated version for downstream consumption

**Success check:** querying the database shows both the individual columns and a well-formed `priority_tag_json` string that, when parsed, reconstructs the exact same information.

---

## Step 5 — Verification Pass

**Task for agent:**
1. Extend the Phase 3 verification script (or create `verify_phase4.py`) to:
   - Pull the last 10 real events from the database
   - Parse each `priority_tag_json` field back into a dict
   - Print it in a clean, readable format confirming every field is present and correctly typed
2. Deliberately test an edge case: an event with `urgency = "low"` and empty `reason_codes` — confirm the tag still builds correctly and doesn't break on the "nothing unusual happened" case

**Success check:** the verification script shows correctly structured priority tags for a range of urgency levels, including the "low, nothing flagged" case, with no missing or malformed fields.

---

## Phase 4 Completion Checklist

- [ ] `PriorityTag` schema formally defined with all required fields
- [ ] `build_priority_tag()` assembles and validates without altering Phase 3's decisions
- [ ] Live pipeline produces a clean priority tag for every event
- [ ] Priority tags are persisted as structured JSON in the database
- [ ] Verification confirms correctness across multiple urgency levels, including the "low" edge case

**Phase 4 ends here.** Do not implement LLM summarization or the dashboard in this phase — Phase 5 will take the `PriorityTag` object as its sole input to generate the plain-English summary, and Phase 6 will render it on the dashboard.
