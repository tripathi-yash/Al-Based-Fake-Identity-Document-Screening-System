# AI-Based Fake Identity & Document Screening System

SIH-style hackathon project  automated document OCR, validation, tampering detection,
face verification, and a blockchain audit trail, built as a border-checkpoint decision-support
system. See `docs/action_plan.pdf` for the full project plan.

## Team / Module Ownership

| Module | Owner | Status |
|---|---|---|
| Module 1  OCR Extraction | | not started |
| Module 2  Document Validation | | not started |
| Module 3  Tampering Detection | | not started |
| Module 4  Face Verification | | not started |
| Module 5  Authority Reference Match (extension) | | not started |
| Module 6  Blockchain Ledger | | not started |
| Risk Scoring Engine | | not started |
| Frontend / Dashboard | | not started |
| Data Fixtures + Mock DBs | | not started |

Fill this in on Day 1 and keep it current  it's the fastest way for anyone on the team
(or a judge asking "who built this part?") to know who to talk to.

## Setup

```bash
# backend
cd backend

## Requirements

- use Python 3.11.9
pip install -r ../requirements.txt

# run the API
uvicorn main:app --reload

# frontend
cd frontend
npm install
npm run dev
```

## Day 1 checklist (do this before writing any real module logic)

1. Read `schema/module_io_schema.json` — this is the exact contract every module must
   produce/consume. Do not change it without telling the whole team.
2. Read `config/doc_types_config.json` and `config/thresholds_config.json` all
   per-document-type rules and tunable thresholds live here, never hardcoded per-file.
3. Every module owner writes their `stub.py` first (Day 2), returning the exact mock
   output already provided in each module folder, so the full pipeline can be wired
   together by Day 2-3 before any real algorithm is finished. See
   `docs/action_plan.pdf` Section 9a/9b for why this matters.
4. Log every test image/fixture you create in `data/fixtures/fixtures_manifest.csv`
   filename, doc type, category, expected result per module. This file is your ground
   truth for `tests/test_integration_pipeline.py`.

## Repo Structure

See `docs/action_plan.pdf` for the full module specs (tech stack, prerequisites, edge
cases owned by each module). Folder layout mirrors the module breakdown directly:

- `backend/modules/module{1-6}_*` one folder per module, each with a `stub.py`
  (mock output, keep forever as a fallback) and the real implementation file(s)
- `backend/risk_engine/` combines Module 2/3/4(/5) outputs into the two-axis risk score
- `backend/database/`  mock DB #1 (issuance/blacklist) and mock DB #2 (authority reference)
- `data/fixtures/`  DIY test images (clean, tampered, face pairs) + the manifest
- `docs/demo_script.md` the rehearsed demo sequence for judging day
