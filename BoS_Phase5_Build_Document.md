# Brain of Sensors (BoS) — Phase 5 Build Document
### Scope: LLM Summarizer — translate the priority tag into a plain-English sentence (translation only, no analysis)
### Target: Google Antigravity (agentic step-by-step execution)
### Depends on: Phase 4 completed (`PriorityTag` schema + `priority_tag_json` persisted to DB)

---

## Phase 5 Objective

Take the structured `PriorityTag` produced in Phase 4 and generate one short, plain-English sentence describing the event — using an LLM strictly as a translator, never as a decision-maker. The LLM must not re-analyze the event, must not change the urgency, and must not introduce any information not already present in the tag. No dashboard yet — this phase only produces and stores the generated sentence.

**Definition of done:** every scored event has a clean, accurate, human-readable one-sentence summary stored alongside it, generated entirely from its `PriorityTag` — never from raw video or logs.

---

## Step 1 — API Setup

**Task for agent:**
1. Add the Anthropic Python SDK (`anthropic`) to `requirements.txt` and install it
2. Create a new file `summarizer.py`
3. Set up API key handling via an environment variable (e.g. `ANTHROPIC_API_KEY`) — never hardcode the key in source files
4. Add a `.env` entry placeholder and confirm `.env` is listed in `.gitignore` if version control is in use

**Success check:** a minimal test call to the API (a simple "hello" prompt) succeeds and returns a response, confirming the API key and SDK setup work correctly.

---

## Step 2 — Design the Constrained Prompt

**Task for agent:**
1. In `summarizer.py`, write a function `build_prompt(priority_tag)` that constructs a strict, narrow prompt from the tag fields only. The prompt must:
   - Present the `PriorityTag` fields as the only source of information (zone, object, timestamp, urgency, reason_codes, live_count, historical_avg)
   - Explicitly instruct the model: *"Using only the data provided below, write one plain-English sentence (maximum 25 words) describing this event. Do not add any information, speculation, or context not present in the data. Do not change or reinterpret the urgency level."*
   - Include the tag's field values formatted clearly in the prompt body
2. Keep the prompt template in one place (this function) so it's easy to adjust later without touching the calling logic

**Success check:** `build_prompt()` produces a clean, well-formatted prompt string when given a sample `PriorityTag`, clearly separating instructions from data.

---

## Step 3 — Build the Summarization Call

**Task for agent:**
1. In `summarizer.py`, write a function `summarize_event(priority_tag)` that:
   - Calls `build_prompt()` to construct the prompt
   - Sends it to the LLM API with a low temperature setting (favor consistency over creativity, since this is translation, not generation)
   - Returns the generated sentence as a plain string
2. Add basic error handling: if the API call fails (timeout, rate limit, etc.), return a safe fallback string built directly from the tag fields without the LLM (e.g. `"{zone}: {object} detected, urgency {urgency}."`) — the system must never fail to produce *some* readable output

**Success check:** calling `summarize_event()` with a sample tag returns a coherent, accurate sentence; temporarily breaking the API key confirms the fallback string still produces a usable (if less polished) summary instead of crashing.

---

## Step 4 — Validate LLM Output Against the Tag

**Task for agent:**
1. Add a lightweight validation function `validate_summary(summary_text, priority_tag)` that checks:
   - The generated sentence does not exceed a reasonable length (e.g. 40 words, allowing some buffer over the 25-word instruction)
   - The stated urgency word (if the model happens to mention "low"/"medium"/"high") does not contradict `priority_tag.urgency`, if present in the text
2. If validation fails, fall back to the safe template string from Step 3 rather than storing a potentially inconsistent LLM output
3. This is a lightweight safety net, not a full fact-checking system — its job is to catch obvious contradictions, not guarantee perfection

**Success check:** feeding a deliberately mismatched test case (e.g. a mock LLM response that says "low priority" for a tag marked `"high"`) triggers the fallback path instead of being stored as-is.

---

## Step 5 — Wire Into the Live Pipeline

**Task for agent:**
1. In `main.py`, after `build_priority_tag()` runs (Phase 4 step), call `summarize_event()` with the resulting tag, then `validate_summary()` on the output
2. Print the final summary sentence to the console alongside the tag for verification during this phase

**Success check:** walking in front of the webcam now prints a full pipeline result — event → score → tag → validated plain-English sentence — end to end in real time.

---

## Step 6 — Persist the Summary

**Task for agent:**
1. In `database.py`, add one new column to the `events` table: `summary_text` (text)
2. Update the event-insertion logic so the validated summary from Step 5 is stored in this column alongside everything from Phases 1–4
3. Ensure synthetic historical events (Phase 2) remain unaffected — they still don't need summaries, same as they don't need urgency scores

**Success check:** querying the database shows real events with a complete row: raw detection fields, urgency/reason_codes, the full priority tag JSON, and now a clean, readable summary sentence.

---

## Step 7 — Verification Pass

**Task for agent:**
1. Extend the verification script (or create `verify_phase5.py`) to print the last 10 real events as: `[urgency] summary_text` in a simple readable list
2. Manually review the output — confirm every summary sentence accurately reflects its tag's zone, object, and urgency, with no invented details

**Success check:** the printed list reads like a believable incident log a human analyst could actually use, with every line traceable back to its underlying structured data.

---

## Phase 5 Completion Checklist

- [ ] API integration working with secure key handling
- [ ] Prompt strictly constrained to tag data only, with explicit no-speculation instruction
- [ ] `summarize_event()` returns accurate sentences, with a safe non-LLM fallback on failure
- [ ] `validate_summary()` catches contradictions between the summary and the tag's urgency
- [ ] Summaries wired into the live pipeline end to end
- [ ] Summaries persisted to the database alongside every real event
- [ ] Verification confirms summaries are accurate, readable, and traceable

**Phase 5 ends here.** Do not implement the dashboard in this phase — Phase 6 will read directly from the database (`priority_tag_json` + `summary_text`) to render the live, ranked, color-coded feed.
