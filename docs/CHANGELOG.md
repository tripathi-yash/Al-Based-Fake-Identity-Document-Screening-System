# Development Changelog

Running log of implementation changes, kept separate from `action_plan.md`
(the plan) so teammates can see what's actually been built/changed without
re-reading the whole action plan. Newest entries at the top. Each entry:
what changed, why, and what's still open/TODO for whoever picks it up next.

---

## 2026-09-04 — Modules 3–6 implementation pass

### Module 3 — Tampering Detection
- **Fixed real bug in `dl_tamper_detector.py`:** `dl_tamper_probability` was
  computed twice — once via 90th-percentile (correct, per design intent),
  then silently overwritten by a `.mean()` calculation right after. Removed
  the duplicate; percentile-90 version now stands. This mattered because a
  small tampered region in an otherwise clean document was getting washed
  out by whole-image averaging.
- No other functional changes to `ela.py`, `exif_check.py`, `copy_move.py`,
  `tampering_detection.py` — fusion logic (DL primary, classical signals
  resolve borderline only) confirmed correct as originally written.

### Module 4 — Face Verification (rewritten)
- Reimplemented `face_verification.py` to match `schema/module_io_schema.json`
  exactly: `status` is `"match"|"mismatch"|"no_face_detected"` (not a
  free-form verdict string), threshold convention is **cosine similarity**
  (higher = more similar), not distance — matches
  `thresholds_config.json`'s documented convention.
- **Added `doc_embedding` field** to the return dict (not in the original
  schema) — required by Module 6b (`identity_reuse.py`) for nearest-neighbor
  search across the ledger. Additive/backward-compatible.
- Extracted shared embedding logic into `backend/modules/shared/
  face_embedding_utils.py` (`get_face_embedding()`, `cosine_similarity()`)
  so Modules 4, 5, and 6 all use the identical model (FaceNet via DeepFace,
  RetinaFace detector backend) and distance metric — no drift between
  modules.
- **New dependency:** `tf-keras` required alongside `deepface`/`retina-face`
  (TensorFlow 2.16+ defaults to Keras 3, which DeepFace/RetinaFace don't yet
  support without the compatibility shim). Added to `requirements.txt`.

### Module 5 — Authority Reference Match (implemented, was stub-only)
- Implemented `authority_match.py` against `backend/database/
  mock_db2_authority_ref.py`'s `AUTHORITY_REFERENCE_TABLE`.
- **Signature change, flagged not silently made:** `stub.py` declares
  `run_authority_match(ocr_result)`, but the module needs the document
  IMAGE to extract a face embedding, which `ocr_result` doesn't carry.
  Real implementation is `run_authority_match(ocr_result, doc_image_bytes)`.
  **`backend/api/routes.py` has NOT been updated to pass `doc_bytes` into
  this call yet — still open.**
- Returns `"not_available"` (not a false negative) when: no passport number
  in `ocr_result`, no authority record for that number, or face extraction
  fails on either image. Per schema, every downstream consumer (risk engine,
  Module 6) must handle `not_available` gracefully.

### Module 6 — Blockchain Audit Layer (combiner + integrity check added)
- **`blockchain_ledger.py` created** — did not exist before (only `stub.py`,
  `hash_chain.py`, `identity_reuse.py` did). Combines 6a (hashing) + 6b
  (identity reuse) into one `write_ledger_record()` call, matching
  `stub.py`'s intended role. `routes.py` should import from here once ready.
- **`hash_chain.py`:** added `verify_chain_integrity()` — the docstring
  already claimed this module "detects tampering with stored past records"
  but no function actually did that verification before. Walks the ledger,
  recomputes every hash, confirms both stored hash and `prev_hash` chaining.
- **`identity_reuse.py`:** implemented `search_for_identity_reuse()` —
  nearest-neighbor cosine similarity search across all prior ledger records,
  flags only when a close face match is found under a DIFFERENT declared
  identity/doc number. Same face under the SAME identity is never flagged
  (expected — same legitimate person rescreened).
- **`ledger_store.py`:** implemented `append_record()`, `get_all_records()`,
  `get_latest_hash()`. Local append-only JSON file at `data/ledger/
  audit_ledger.json` stands in for real distributed storage in this
  prototype — say this plainly if asked in Q&A.
- **`write_ledger_record()` gained a 6th optional parameter
  `authority_result=None`** — Module 5's match/mismatch/not_available status
  and similarity are now preserved in the permanent ledger record, not just
  printed and discarded. Optional so callers that don't pass it yet (e.g.
  current `routes.py`) don't break.
- Verified end-to-end manually: same face reused under two different
  declared identities correctly produced `identity_reuse_flag: True` (see
  test run 2026-09-04).

### Config (`config/thresholds_config.json`)
- Added `authority_reference_match.match_threshold` (0.6, placeholder —
  starts equal to `face_verification`'s threshold, tune separately once
  Module 5 has real reference photos).
- Added `identity_reuse_detection.similarity_threshold` (0.6, placeholder —
  was previously hardcoded directly in `identity_reuse.py`).
- Flagged: `risk_scoring.module_weights` still only has 3 keys (validation,
  tamper, face) — does NOT yet account for Module 5 mismatch or Module 6
  identity-reuse flag. Recommendation (pending team decision): treat both as
  **override/escalation signals**, not blended weights — a confident Module
  5 mismatch or a Module 6 reuse flag should force high risk regardless of
  the weighted score, same non-diluting-veto principle as Module 3's
  DL-primary fusion logic. Not yet implemented in `risk_engine/scoring.py`.

### New: `scripts/generate_tampered_fixtures.py`
- Generates 6 categories of DIY tampered fixtures programmatically from
  `data/fixtures/clean/` base images: `copy_move`, `splice`, `recompress`,
  `exif_strip`, `exif_inject`, `combined`. Outputs to `data/fixtures/
  tampered/<category>/` plus a `manifest.json` with ground truth per file.
  New dependency: `piexif`.

---

## OPEN / NOT YET DONE (as of this entry)

- [ ] `backend/api/routes.py` not updated: doesn't pass `doc_bytes` to
      `run_authority_match()`, doesn't call Module 5 at all currently, still
      imports Module 6 from `stub.py` instead of `blockchain_ledger.py`.
- [ ] `risk_engine/scoring.py` doesn't consume Module 5 or Module 6 output
      yet — override-signal logic discussed but not implemented.
- [ ] `data/fixtures/faces/matched/` and `mismatched/` are empty — need 5-6
      matched pairs + 3-4 mismatched pairs (per action plan) before Day 5
      threshold tuning can happen for Module 4.
- [ ] `mock_db2_authority_ref.py`'s `AUTHORITY_REFERENCE_TABLE` has only
      placeholder/test entries — needs real fixture passport numbers once
      Module 1 OCR is reliable.
- [ ] `data/fixtures/fixtures_manifest.csv` still empty (header only) — not
      being filled in as fixtures are generated.
- [ ] `data/ledger/` added to `.gitignore` (generated runtime output, not
      committed) — confirm this lands before next push.
- [ ] Modules 1 (OCR) and 2 (Validation) still stub-only — everything above
      has only been tested with fake/hand-built `ocr_result` dicts, not real
      extraction.
- [ ] Frontend - not done
