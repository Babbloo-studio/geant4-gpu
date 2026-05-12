# BD-geant4-001 claim metadata preflight (2026-05-12)

Scope: compact fail-closed prerequisite iteration for `BD-geant4-001` after the
L1-to-harness triage. This closes only the claim-level/metadata propagation
prerequisite from `docs/reports/g4_bd001_l1_to_harness_triage.md`; it does not
unblock a measurement.

## Claim-level and metadata propagation

Current harness evidence:

- `benchmarks/harness/run.py` imports `CLAIM_LEVELS` from the schema layer.
- `_plan_scripts(...)` passes `claim_level`, `geant4_version`, and `notes` into
  `RunnerSpec` instead of leaving rendered scripts at the default `L0` metadata.
- `_validate_run_args(...)` rejects unknown claim levels, rejects non-empty notes
  for `L3`, and rejects blank Geant4 version strings.
- `benchmarks/harness/tests/test_run.py` includes a `BD-geant4-001` dry-run case
  requiring `CLAIM_LEVEL=L2`, `GEANT4_VERSION=v11.2.2-bd001-preflight`, and the
  rendered `--claim-level`, `--geant4-version`, and `--notes` collector args.

## Remaining BD-geant4-001 blockers

This preflight does **not** resolve the other BD-001 blockers:

1. no Moller/Bhabha inverse-sampler implementation branch exists;
2. no optimized Geant4 fork/prefix builder path is proven;
3. no `benchmarks/optimizations_registry.yaml` row exists;
4. no sampler-level validation exists for sampled `x`, delta-ray kinetic energy,
   angle, and downstream energy loss;
5. the `PHYSICS_LIST` selector is still recorded in the script but not proven to
   be honored by the W1/W2 binaries.

Therefore `BD-geant4-001` remains fail-closed before any harness row or claim.

## Verification

```bash
/projects/hep/fs10/shared/nnbar/billy/packages/hibeam_env/bin/python \
  scripts/verify_bd001_claim_metadata_preflight.py
```

Expected marker: `BD001_CLAIM_METADATA_PREFLIGHT_OK`.

No SLURM submit/cancel/dry-run via `sbatch`, event run, result row, reference
regeneration, NNBAR production edit, speedup claim, or parity claim is made by
this preflight.
