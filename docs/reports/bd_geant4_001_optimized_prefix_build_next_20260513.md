# BD-geant4-001 optimized-prefix build-next blocker — 2026-05-13

This compact build-next iteration ran the existing fail-closed optimized-prefix
preflight gates and did **not** build Geant4, submit SLURM, run benchmark
events, generate sampler Parquets, append `benchmarks/results/results.parquet`,
or claim parity/speedup.

## Source and target evidence

- Geant4 source repo: `/projects/hep/fs10/shared/nnbar/billy/geant4-fork`
- Required source commit: `4ac150b`
- Required handoff head: `782d84c`
- Candidate flag: `-DG4EM_MOLLER_BHABHA_INVERSE_SAMPLER=ON`
- Target prefix: `/projects/hep/fs10/shared/nnbar/billy/pending/bd001-optimized-geant4`
- Required config path:
  `/projects/hep/fs10/shared/nnbar/billy/pending/bd001-optimized-geant4/lib/cmake/Geant4/Geant4Config.cmake`

`git merge-base --is-ancestor 4ac150b 782d84c` is the required source-ref
relationship, and the handoff source keeps the default-off inverse-sampler flag
plus the vanilla `flatArray(2, rndm)` fallback guarded by the preflight verifier.

## Fail-closed build decision

`OPEN: optimized_prefix_build_compute_resource_missing` — this lane has no fresh
planner-approved compute allocation for the install build. The guarded wrapper
therefore remains the authoritative command to run later:

```bash
BD001_OPTIMIZED_PREFIX_BUILD_APPROVED=YES \
  /projects/hep/fs10/shared/nnbar/billy/geant4-gpu/scripts/prepare_bd001_optimized_prefix.sh
```

The wrapper must see `SLURM_JOB_ID` from an approved compute job unless a future
planner goal explicitly sets `BD001_ALLOW_NON_SLURM_PREFIX_BUILD=YES`. Without
approval it exits with `BD001_OPTIMIZED_PREFIX_PREFLIGHT_BLOCKED`; with approval
but no compute allocation it exits with `BD001_OPTIMIZED_PREFIX_COMPUTE_GUARD`.
It must refuse a nonempty target prefix before any install.

## Readiness state

The current compact-safe state remains blocked, not promoted:

- `OPEN: optimized_prefix_config_missing`
- `BD001_OPTIMIZED_PREFIX_PREFLIGHT_BLOCKED_OK`
- `BD001_RESULT_READINESS_OPTIMIZED_PREFIX_BLOCKED_OK`
- `BD001_RESULT_READINESS_RESULTS_ROW_BLOCKED_OK`
- `BD001_OPTIMIZED_PREFIX_BUILD_NEXT_BLOCKED_OK`

If a later guarded build creates `Geant4Config.cmake`, this blocker report and
verifier must be replaced by digest-pinned prefix evidence before any sampler
validation, smoke run, measured result row, parity claim, or speedup claim.

## Verification contract

- `scripts/verify_bd001_optimized_prefix_build_next.py`
- Existing focused gates:
  `scripts/verify_bd001_optimized_prefix_preflight.py` and
  `scripts/verify_bd001_result_readiness.py`

No SLURM submit/cancel/requeue/resubmit/dry-run/allocation was performed for
this report. No benchmark events, result rows, reference mutations, NNBAR
production edits, parity claims, or speedup claims were produced.
