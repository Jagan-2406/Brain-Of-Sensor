# Brain of Sensors (BoS) — Patch: Object Risk Weighting in Rules Engine
### Scope: Fix false-priority bug in Phase 3 (`rules_engine.py`) — rare-but-harmless objects scoring higher than relevant-but-common ones
### Target: Google Antigravity (agentic step-by-step execution)
### Depends on: Phases 1–6 complete and working
### Hard constraint: this patch must ONLY modify `rules_engine.py`. No other file, table, schema, or phase's behavior may change.

---

## Bug Being Fixed

The current scoring logic in `score_event()` (Phase 3) computes urgency purely from **frequency vs. historical average**, with no concept of object risk. This causes two incorrect outcomes:

1. A **person** appearing in a zone stays `low` priority as long as it's within normal frequency for that zone — even in cases where a person's presence is inherently more relevant to a security context.
2. A **rare object** (e.g. a mobile phone, detected once where the historical average is near zero) produces a very large frequency multiplier purely from dividing by a near-zero baseline — incorrectly scoring `high`, despite being harmless.

**Root cause:** the engine measures statistical rarity, not actual relevance/risk. This patch adds an object-risk weighting layer and a baseline floor, without touching frequency logic's core structure.

---

## Non-Negotiable Isolation Rules

1. Only `rules_engine.py` may be edited. Do not touch `database.py`, `priority_tag.py`, `summarizer.py`, `main.py`, `app.py`, `target_detection.py`, or any HTML/JS files.
2. Do not change the function signature of `score_event(event)` — it must accept and return exactly the same shape as before, so Phase 4 (`build_priority_tag()`) and everything downstream continues to work without modification.
3. Do not change the database schema in any way.
4. Existing named constants (`HIGH_MULTIPLIER`, `MEDIUM_MULTIPLIER`, `NIGHT_HOURS`) must remain as-is — this patch adds new constants and logic alongside them, it does not replace or rename the existing ones.

---

## Step 1 — Back Up Current Behavior for Comparison

**Task for agent:**
1. Before making any changes, run the existing Phase 3 verification script (`verify_phase3.py` or equivalent) and save its output to a new file `pre_patch_baseline.txt`
2. This file is the reference used later in Step 6 to confirm the fix worked and nothing else broke

**Success check:** `pre_patch_baseline.txt` exists and contains the urgency/reason_codes output for a known set of test events, including at least one "person" event and one "cell phone" (or similarly rare object) event showing the current, incorrect behavior.

---

## Step 2 — Add Object Risk Weight Table

**Task for agent:**
1. Open `rules_engine.py`. Near the top, alongside the existing named constants (`HIGH_MULTIPLIER`, etc.), add a new constant:
   ```python
   # Assigns a relative risk weight per detected object class.
   # This corrects for statistical rarity being mistaken for actual risk —
   # e.g. a rarely-seen harmless object (like a phone) should not outscore
   # a commonly-seen but security-relevant object (like a person).
   OBJECT_RISK_WEIGHT = {
       "person": 1.0,
       "vehicle": 0.8,
       "backpack": 0.4,
       "cell phone": 0.05,
       "chair": 0.0,
       "bottle": 0.0,
   }
   DEFAULT_RISK_WEIGHT = 0.1  # applied to any object class not explicitly listed
   ```
2. Add a one-line comment above the dict explaining these values can be tuned later without changing the scoring logic itself

**Success check:** the file parses with no syntax errors; the new constants are clearly separated from and do not overwrite the existing threshold constants.

---

## Step 3 — Add a Baseline Floor to Prevent Divide-by-Near-Zero Blowups

**Task for agent:**
1. Still near the top of `rules_engine.py`, add:
   ```python
   # Prevents runaway multipliers when an object's historical average is
   # near zero (e.g. an object rarely or never seen before in this zone).
   # Without this floor, a single rare detection can appear as a massive
   # statistical anomaly even though it poses no real risk.
   MIN_BASELINE = 0.1
   ```
2. Locate the exact line(s) inside `score_event()` where `historical_average` (from `get_zone_history()`) is used in a division or ratio calculation
3. Immediately before that calculation, insert:
   ```python
   safe_average = max(historical_average, MIN_BASELINE)
   ```
4. Replace the existing use of `historical_average` in the ratio/multiplier calculation with `safe_average` — this is the only change to the existing frequency logic, and it must not alter any other part of that calculation

**Success check:** re-running a test case with a near-zero historical average (e.g. the "cell phone" case from Step 1) no longer produces an inflated multiplier purely from dividing by a tiny number.

---

## Step 4 — Apply Risk Weight to the Final Score

**Task for agent:**
1. Inside `score_event()`, after the existing frequency-based multiplier/urgency logic has run and produced its intermediate result (but before the function returns), add a new step that applies the risk weight:
   ```python
   risk_weight = OBJECT_RISK_WEIGHT.get(event["object"], DEFAULT_RISK_WEIGHT)
   ```
2. Use `risk_weight` to adjust the final urgency decision. The simplest, lowest-risk-of-breaking-things approach:
   - If `risk_weight <= 0.1`: cap the final urgency at `"low"` regardless of what the frequency logic computed, and add `"low_risk_object_class"` to `reason_codes`
   - Otherwise: leave the frequency-based urgency decision as-is (this patch does not need to scale every score numerically — capping low-risk objects is enough to fix the reported bug without introducing new untested scoring math)
3. Do not remove or bypass any existing `reason_codes` already being added by the frequency logic — this step only adds an additional cap/reason code on top

**Success check:** a "cell phone" test event that previously scored `high` purely from frequency now scores `low`, with `"low_risk_object_class"` present in its `reason_codes`. A "person" test event that legitimately triggers high frequency (e.g. an actual unusual burst) still correctly scores `high` — the fix does not suppress genuine anomalies for high-risk object classes like "person."

---

## Step 5 — Confirm Output Shape Is Unchanged

**Task for agent:**
1. Verify that `score_event()` still returns exactly the same dictionary shape as before this patch:
   ```python
   {
     "urgency": "low" | "medium" | "high",
     "reason_codes": [...],
     "historical_average": <float>,
     "live_count": <int>
   }
   ```
2. Confirm no new required fields were added to this return value — `OBJECT_RISK_WEIGHT` and `MIN_BASELINE` are internal implementation details of this function, not part of its output contract

**Success check:** Phase 4's `build_priority_tag()` and everything downstream (Phase 5, Phase 6) continues to work completely unmodified, because the function's input/output contract is unchanged.

---

## Step 6 — Full Verification Against Baseline

**Task for agent:**
1. Re-run the same verification script used in Step 1, producing `post_patch_result.txt`
2. Compare `pre_patch_baseline.txt` and `post_patch_result.txt` side by side:
   - The "cell phone" (or similarly rare/harmless object) test case must now show `"low"` instead of its previous incorrect `"high"`
   - Any "person" test case that was correctly flagged before (a genuine anomaly) must still be flagged the same way — no regression
   - Any event that was correctly `"low"` before must remain `"low"`
3. Run the full end-to-end system (Phases 1–6 live, plus the target detection feature if enabled) for a few minutes and confirm:
   - The dashboard, database schema, LLM summaries, and priority tags all continue to function exactly as before, with only the urgency *values* for low-risk object classes changing
   - No errors, no schema changes, no broken downstream phase

**Success check:** side-by-side comparison shows the specific bug is fixed (phone no longer high, person logic unaffected), with zero regressions anywhere else in the pipeline.

---

## Patch Completion Checklist

- [ ] Baseline output captured before any changes
- [ ] `OBJECT_RISK_WEIGHT` table added without touching existing constants
- [ ] `MIN_BASELINE` floor added, applied only inside the existing ratio calculation
- [ ] Risk-weight capping logic added without removing existing frequency-based logic
- [ ] `score_event()` return shape confirmed unchanged
- [ ] Post-patch verification confirms the bug is fixed and no other event/phase behavior regressed
- [ ] Only `rules_engine.py` was modified — no other file touched

**This patch is complete when the side-by-side baseline comparison in Step 6 passes cleanly, with the phone/person scoring issue resolved and every other previously-verified behavior intact.**
