# Bovine Visual Asset Readiness

## Scope And Boundary

- Source-verified PDFs: 3.
- Deterministic field-aware candidate pages: 12.
- Extracted visual assets: 12.
- This stage extracts embedded images and records source/layout hashes. It does
  not interpret plots, transcribe scientific numbers, assign treatment/control
  roles, or approve an evidence tier.

## Result

- Strict group-statistics visual candidates: 6.
- Broader visual candidates: 6.
- Assets mapped to verified JATS figure IDs: 4/12.
- Nonblank pixel check: 12/12 passed.
- Unique JATS supplement references: 2; available locally: 0.
- All 12 extracted nonblank assets are ready for bounded visual review. The
  strict candidates should be reviewed first; broader candidates are not
  assumed to contain complete mean-dispersion-n structures.

## Safety And Availability

- Image files remain generated local assets under `data/visual_assets/bovine-baseline-v1`; the
  committed inventory contains paths, hashes, dimensions, and locators only.
- R016 and R022 licenses and JATS hashes come from the verified acquisition
  registry. R021's CC BY status is verified from its hash-bound PDF text.
- Missing supplement files remain `referenced_not_local`; a JATS href alone is
  not reported as a locally available asset.

## Reproduction

```bash
python scripts/build_bovine_visual_assets.py
```
