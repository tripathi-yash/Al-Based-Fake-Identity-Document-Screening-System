# Demo Script — Rehearsed Sequence for Judging Day

See action_plan.pdf Section 14 for full context. Fill in the actual filenames
once fixtures are built (Day 4), so the demo can be run without improvising
which file to click on.

Rehearse this exact sequence at least twice before submission day.

## 1. Clear document — full pass
- **File:** `data/fixtures/clean/____________`
- **Expected:** all modules green, risk_band = clear, evidence_band = high

## 2. Digitally tampered document
- **File:** `data/fixtures/tampered/____________`
- **Expected:** Module 3 flags overall_tamper_flag = true, risk_band = high_risk
- **Talking point:** explain ELA heatmap on screen — this is your "core AI innovation" moment

## 3. Photo swapped to a different, wrong person
- **File:** `data/fixtures/faces/mismatched/____________`
- **Expected:** Module 4 status = mismatch, risk_band = high_risk

## 4. Blacklisted / expired document
- **File:** `data/fixtures/____________` (linked_db_id in manifest must match a blacklisted entry in mock_db1_issuance.py)
- **Expected:** Module 2 db_status = blacklisted or expired, risk_band = high_risk

## 5. Flawless-forgery-style fixture (if Module 5 is built)
- **File:** `data/fixtures/____________`
- **Expected:** Module 4 = match (own face swapped in cleanly), Module 5 = mismatch
  (doesn't match authority reference) — **this is your strongest differentiation
  moment, do not skip if Module 5 is built.**
- **Talking point:** this is exactly the scenario discussed in action_plan.pdf
  Section 6/7 — document-only verification's theoretical ceiling, and how
  Module 5 closes it.

## 6. Blockchain ledger + identity reuse
- Show the ledger view (Module 6a hash chain) after several screenings.
- If time allows, re-submit a fixture under a different declared name to
  trigger `identity_reuse_flag = true` (Module 6b) live.

## Backup plan
Have a recorded video of this exact sequence ready, in case live demo or
network fails during judging.

## Q&A ownership reminder
Per action_plan.pdf Section 14 — every teammate should be ready to explain
at least one module here, even if they didn't write all the code for it.
