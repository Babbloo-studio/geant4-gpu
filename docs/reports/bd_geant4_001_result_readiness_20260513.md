# BD-geant4-001 measured-result readiness — 2026-05-13

This is a fail-closed readiness snapshot for the first future BD001 measured
result row. It verifies gaps only; it does not authorize SLURM, event/reference
runs, result-row writes, NNBAR production edits, parity claims, or speedup
claims.

## Current blockers

- `OPEN: approved_review_artifact_missing_or_blocked` — the default
  `benchmarks/optimizations_registry.yaml` row still has `review_status:
  blocked`, so `bd001_review_gate(...)` must reject it before any measured run.
- `OPEN: optimized_prefix_config_missing` — the registry points at the pending
  optimized Geant4 prefix
  `/projects/hep/fs10/shared/nnbar/billy/pending/bd001-optimized-geant4`,
  and no `lib/cmake/Geant4/Geant4Config.cmake` exists there. Source evidence
  is pinned to source commit `4ac150b`, handoff head `782d84c`, and CMake flag
  `-DG4EM_MOLLER_BHABHA_INVERSE_SAMPLER=ON`. A later approved compute build
  should use guarded wrapper `scripts/prepare_bd001_optimized_prefix.sh`; it
  exits `BD001_OPTIMIZED_PREFIX_PREFLIGHT_BLOCKED` unless
  `BD001_OPTIMIZED_PREFIX_BUILD_APPROVED=YES` is set by a fresh planner goal.
- `OPEN: sampler_validation_parquets_missing` — the required sampler-observable
  files are not staged under `benchmarks/validation/bd001_sampler/`:
  `vanilla_sampler_observables.parquet` and
  `optimized_sampler_observables.parquet`.
- `OPEN: canonical_results_parquet_missing` — there is no canonical
  `benchmarks/results/results.parquet` result-row table to audit for BD001.

## Guardrail

`scripts/verify_bd001_result_readiness.py` must continue to print
`BD001_RESULT_READINESS_BLOCKED_OK` until the above blockers are replaced by an
approved review artifact, optimized-prefix install evidence, sampler-validation
Parquets covering `sampler_x`, `delta_ray_ke_mev`, `delta_ray_theta_rad`, and
`downstream_dedx_mev_mm`, and a fresh guarded smoke/result-row planner goal.

No SLURM submission, benchmark execution, Parquet generation, result append,
NNBAR production edit, parity claim, or speedup claim was performed.
