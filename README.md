# AI-Based Fake Identity & Document Screening System

SIH-style hackathon project — automated document OCR, validation, tampering detection,
face verification, and a blockchain audit trail, built as a border-checkpoint decision-support
system. See `docs/action_plan.pdf` for the full project plan and `docs/CHANGELOG.md` for a
running log of what's actually been implemented so far.

## Team / Module Ownership

| Module | Owner | Status |
|---|---|---|
| Module 1 — OCR Extraction | | stub only |
| Module 2 — Document Validation | | stub only |
| Module 3 — Tampering Detection | | implemented, pending fixture calibration |
| Module 4 — Face Verification | | implemented, pending threshold tuning (need `data/fixtures/faces/` pairs) |
| Module 5 — Authority Reference Match (extension) | | implemented, pending real mock DB entries + `routes.py` wiring |
| Module 6 — Blockchain Ledger | | implemented, verified end-to-end |
| Risk Scoring Engine | | stub only — Module 5/6 override-signal logic not yet wired in |
| Frontend / Dashboard | | not started |
| Data Fixtures + Mock DBs | | partial — tampered-fixture generator ready, face pairs + manifest still empty |

Fill in the Owner column and keep Status current — it's the fastest way for anyone on the
team (or a judge asking "who built this part?") to know who to talk to. See
`docs/CHANGELOG.md` for the detailed technical log behind each status above, including open
TODOs per module.

## Setup

**Requires Python 3.11.9.**

Run all of this from the project root (the top-level folder you get after cloning —
its name doesn't matter, these commands don't depend on it).

```bash
# 1. Create and activate a virtual environment at project root
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 2. Install dependencies (run from project root, NOT from inside backend/)
pip install -r requirements.txt

# 3. Now move into backend/ to run the API — main.py's relative imports
#    expect this to be the current directory
cd backend
uvicorn main:app --reload

# frontend (separate terminal, back at project root)
cd frontend
npm install
npm run dev
```

If `pip install -r requirements.txt` gives you version conflicts on your machine, use
`requirements-lock.txt` instead — it's an exact known-working snapshot (including
transitive dependencies) from a machine that has run the full pipeline successfully:
```bash
pip install -r requirements-lock.txt
```

### One-time setup: ManTraNet (Module 3 — do this separately, after the pip install above)

`mantranet_lib/` is vendored third-party code and is **not** committed to this repo (see
`.gitignore`) — you must clone and set it up locally:

```bash
cd backend/modules/module3_tampering
git clone https://github.com/RonyAbecidan/ManTraNet-pytorch.git mantranet_lib
```
Then follow that repo's README/demo notebook to download the pretrained weights file
(`MantraNetv4.pt`) into `mantranet_lib/MantraNet/`. `torch`/`torchvision` are already
covered by `requirements.txt` — no separate install needed for those.

## Day 1 checklist (do this before writing any real module logic)

1. Read `schema/module_io_schema.json` — this is the exact contract every module must
   produce/consume. Do not change it without telling the whole team.
2. Read `config/doc_types_config.json` and `config/thresholds_config.json` — all
   per-document-type rules and tunable thresholds live here, never hardcoded per-file.
3. Every module owner writes their `stub.py` first (Day 2), returning the exact mock
   output already provided in each module folder, so the full pipeline can be wired
   together by Day 2-3 before any real algorithm is finished. See
   `docs/action_plan.pdf` Section 9a/9b for why this matters.
4. Log every test image/fixture you create in `data/fixtures/fixtures_manifest.csv` —
   filename, doc type, category, expected result per module. This file is your ground
   truth for `tests/test_integration_pipeline.py`.

## Repo Structure

See `docs/action_plan.pdf` for the full module specs (tech stack, prerequisites, edge
cases owned by each module). Folder layout mirrors the module breakdown directly:

- `backend/modules/module{1-6}_*` — one folder per module, each with a `stub.py`
  (mock output, keep forever as a fallback) and the real implementation file(s)
- `backend/modules/shared/` — face-embedding utilities shared by Modules 4, 5, and 6
  (same model/detector/distance-metric everywhere — do not duplicate this logic per module)
- `backend/risk_engine/` — combines Module 2/3/4/5/6 outputs into the two-axis risk score
- `backend/database/` — mock DB #1 (issuance/blacklist), mock DB #2 (authority reference),
  and the append-only ledger storage layer for Module 6
- `data/fixtures/` — DIY test images (clean, tampered, face pairs) + the manifest.
  `data/midv500_subset/` and `data/ledger/` are gitignored (large/generated data — see
  their `.gitkeep` placeholders); everything else under `data/fixtures/` is committed.
- `scripts/generate_tampered_fixtures.py` — generates the DIY tampered fixture set
  programmatically from `data/fixtures/clean/`
- `docs/CHANGELOG.md` — running technical changelog, separate from the static action plan
- `docs/demo_script.md` — the rehearsed demo sequence for judging day