# BD-geant4-001 smoke readiness blocker

Date: 2026-05-12
Lane: `g4gpu-phase5-bd001-smoke-readiness`
Scope: compact fail-closed readiness evidence only. No SLURM submission, event
execution, reference regeneration, result-row append, parity claim, speedup
claim, optimized-prefix claim, or NNBAR production edit was performed.

## Readiness checklist

| Prerequisite | Current gate |
|---|---|
| approved review artifact | Default registry row remains `review_status: blocked`; `bd001_review_gate` rejects it before script emission. |
| optimized Geant4 prefix | The registry prefix is under `pending/`; `bd001_branch_gate(..., require_prefix_config=True)` fails on missing `Geant4Config.cmake`. |
| sampler validation | `bd001_sampler_observable_gate` requires sampled `x`, delta-ray kinetic energy, delta-ray angle, and downstream `dE/dx`; no production BD001 validation Parquets are present. |
| guarded smoke/result-row | `bd001_guarded_smoke_contract` rejects promotional `SPEEDUP`/paper claims and requires explicit no-promotion checks; canonical `benchmarks/results/results.parquet` is absent. |

## Boundary

This readiness pass only composes existing fail-closed gates and records why a
future BD001 smoke/result-row goal must stay blocked until review, prefix,
sampler-validation, and guarded-contract evidence are all present. It does not
authorize `--submit`, event execution, reference refresh, result-row append, or
parity/speedup promotion.

Expected verifier marker:

```text
BD001_SMOKE_READINESS_BLOCKED_OK
```
