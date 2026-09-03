# Module 3 Architecture Update — DL-Primary, Classical-Supporting

**Date of change:** post-initial-build revision, based on a technical review of
the original ELA+EXIF+SIFT-only design.

## What changed

**Before:**
```
Tampering Core
 ├── ELA
 ├── EXIF
 └── SIFT/ORB copy-move
```

**After:**
```
Tampering Core
 ├── ManTraNet (pretrained DL forgery localizer)  <- PRIMARY
 ├── ELA                                          <- supporting
 ├── EXIF                                         <- supporting
 └── SIFT + RANSAC copy-move                      <- supporting (rebuilt)
```

## Why

Each classical technique alone has a real, well-documented weakness:

| Technique | Weakness | Why it matters |
|---|---|---|
| ELA | Signal weakens if the attacker flattens and recompresses the whole image after editing | A forger doesn't have to "forget" to do this — it's a known evasion |
| EXIF | Strippable (WhatsApp, screenshots, most platforms already strip it from legitimate images) or forgeable | Absence of a suspicious tag is not proof of authenticity |
| Naive SIFT copy-move | Documents legitimately contain repeated patterns (security textures, borders, seals) — naive keypoint-count thresholding false-positives on these | A false "forged" flag on a genuine document is a serious credibility failure in front of judges |

None of these are reasons to drop the techniques — they're reasons not to rely on any single one as proof. The fix:

1. **Add a pretrained deep-learning forgery localizer (ManTraNet) as the primary signal.** It doesn't rely on any single fragile assumption (JPEG recompression history, metadata presence, or exact duplicate keypoints) — it's trained to recognize statistical manipulation traces directly (noise inconsistency, boundary artifacts, texture anomalies).
2. **Rebuild copy-move detection with RANSAC geometric consistency**, so it only flags when many matched keypoints agree on a single consistent transform — this is what separates "this region was actually copy-pasted" from "this document has a repeating pattern."
3. **Fuse all signals with defined rules** (see `tampering_detection.py`) rather than treating each as independently decisive. ELA/EXIF/copy-move never override a confident DL verdict — they only resolve borderline DL scores.
4. **Never force a binary verdict when evidence is weak.** `tamper_verdict` can be `"uncertain"`, which should lower `evidence_strength` in the risk engine (per action_plan.pdf Section 5) rather than silently reading as "clean."

## What to say if a judge pushes on this (direct answers to the exact questions this change was designed to survive)

**"Why are you using ELA? What happens if the attacker recompresses the entire image?"**
> "ELA is supporting evidence, not our primary detector — our primary signal is a pretrained deep-learning forgery localizer that doesn't depend on JPEG compression history at all. ELA adds an extra, independent signal precisely because we know it has that specific weakness."

**"EXIF metadata can be stripped. How do you detect a forged screenshot?"**
> "Correct, and that's why EXIF never gets veto power in either direction in our fusion logic — a clean EXIF read doesn't clear a document, and a suspicious tag doesn't alone convict one. The DL model doesn't depend on metadata surviving at all."

**"SIFT detects similar keypoints — how do you avoid false positives on repeated legitimate patterns?"**
> "Our copy-move detector doesn't flag on keypoint similarity alone — it requires RANSAC to confirm that a large cluster of matches agrees on one consistent geometric transform. A repeated security pattern produces scattered matches with no consistent transform, so it doesn't pass that check."

**"Is your DL model trained specifically on passports/IDs?"**
> Be honest: "No — it's a general-purpose pretrained forgery localizer trained on splicing, copy-move, and other manipulation types across natural images. We use it because a document-specific pretrained model with usable, quickly-integrable weights doesn't exist in a form we could responsibly deploy in our timeframe [DocTamper/DTD is real but is research code requiring custom training infrastructure]. Being general-purpose is a real limitation worth naming, and it's still meaningfully stronger than relying on classical heuristics alone."

## Setup dependency this change introduces

`dl_tamper_detector.py` requires the `mantranet_lib/` vendored dependency
(cloned from `RonyAbecidan/ManTraNet-pytorch`, not pip-installable) and its
pretrained weights file. See that file's docstring for exact setup steps.
**Do this on Day 3, first thing**, before writing any code that depends on
it — if setup takes longer than expected, `tampering_detection.py` already
has a defined fallback to classical-only signals, so the rest of the
pipeline is never blocked on this.
