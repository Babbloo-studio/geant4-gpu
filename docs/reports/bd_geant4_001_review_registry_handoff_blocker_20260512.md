# BD-geant4-001 reviewed production-registry handoff blocker

Date: 2026-05-12
Lane: `g4gpu-phase5-bd001-review-registry`
Scope: compact fail-closed prerequisite only. No SLURM submission, event
execution, reference regeneration, result-row append, parity claim, speedup
claim, optimized install-prefix claim, or NNBAR production edit was performed.

## Decision

No approved review artifact exists yet for the real sampler scaffold, so the
production registry handoff is intentionally blocked rather than measurement
ready.

A default `benchmarks/optimizations_registry.yaml` now contains only a blocked
`BD-geant4-001` handoff row:

- branch: `lane/bd-geant4-001-moller-bhabha-inverse-sampler`
- source-bearing commit: `4ac150bf453fe4dd0e384065c6b8d14cbf0fbc5e`
- handoff head: `782d84cb598f7ca4faa9a67092271dfc2e86d811`
- default-off flag: `G4EM_MOLLER_BHABHA_INVERSE_SAMPLER`
- vanilla fallback token preserved: `flatArray(2, rndm)`
- current status: `review_status: blocked`

`benchmarks.harness.run --require-registry` now composes the source-backed
`bd001_review_gate` for `BD-geant4-001`, so the blocked row fails before any
sbatch script can be used for a BD001 optimized run.

## Prompt-to-artifact mapping

| Requirement | Evidence / disposition |
|---|---|
| Re-inspect the 782d84c scaffold evidence | Verifier checks `/projects/hep/fs10/shared/nnbar/billy/geant4-fork` is on `lane/bd-geant4-001-moller-bhabha-inverse-sampler` at handoff head `782d84c` with source commit `4ac150b` as ancestor. |
| Name source commit, handoff head, default-off flag, vanilla fallback, and remaining blockers | This report and the blocked registry row name all of them. |
| Keep registry use fail-closed without approval | `review_status: blocked` plus `run.py` review-gate enforcement rejects `--require-registry` BD001 dry-runs before script emission. |
| Reject stale/mismatched source commits | Verifier creates a temporary approved fixture with `reviewed_commit=4ac150b` while the branch gate resolves `782d84c`; `bd001_review_gate` rejects it. |
| Do not promote measurement readiness | No production approved row, optimized install prefix, sampler validation Parquet, guarded smoke, result row, parity result, or speedup result was created. |

## Remaining blockers

1. Approved review artifact tied to both source commit `4ac150b` and handoff head
   `782d84c`.
2. Optimized Geant4 install prefix built from the reviewed source ref.
3. Sampler-observable validation Parquets for sampled `x`, delta-ray kinetic
   energy, delta-ray angle, and downstream `dE/dx` / energy-loss observables.
4. Guarded smoke contract with non-promotional result-tag and claim-level.
5. Only after the above: a fresh planner-approved SLURM smoke/result-row goal.

## Verification

Expected verifier marker:

```text
BD001_REVIEW_REGISTRY_HANDOFF_BLOCKED_782D84C_OK
```

Latest local verification used:

```bash
/projects/hep/fs10/shared/nnbar/billy/packages/hibeam_env/bin/python \
  scripts/verify_bd001_review_registry_handoff.py
```

This verification is static/read-only and performs no SLURM submission, event
execution, reference generation, result-row append, parity claim, speedup claim,
or NNBAR production edit.
