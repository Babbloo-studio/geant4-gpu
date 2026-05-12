# BD-geant4-001 L1-to-harness triage (2026-05-12)

Scope: bounded lane-swap triage for `BD-geant4-001` from
`docs/reports/bottleneck_database_geant4.md`. This report does not implement the
Moller/Bhabha sampler, submit SLURM, run events, append result rows, or promote a
speedup/parity claim.

## Source anchor

- Geant4 source tree: `/projects/hep/fs10/shared/nnbar/billy/geant4-fork`
- Version: `v11.2.2`, commit `f840b5da3a70c2c7be836fdb72a781eab12e0af6`
- File: `source/processes/electromagnetic/standard/src/G4MollerBhabhaModel.cc`
- Function: `G4MollerBhabhaModel::SampleSecondaries`, lines 266--350
- Hot loop: Moller branch lines 303--318 and Bhabha branch lines 334--349 call
  `flatArray(2, rndm)` and repeat a rejection loop until accepted.

## Current harness state

- No local or remote implementation branch matching `moller`, `bhabha`,
  `BD-geant4-001`, or `inverse` exists in the current `geant4-gpu` checkout.
- No `benchmarks/optimizations_registry.yaml` entry exists for `BD-geant4-001`.
- Therefore this iteration cannot honestly dry-run a real optimized branch. The
  correct status is **BLOCKED: implementation branch and registry metadata
  missing**.

## Harness mapping once unblocked

First smoke target:

```bash
python -m benchmarks.harness.run \
  --opt-id BD-geant4-001 \
  --opt-branch lane/bd-geant4-001-moller-bhabha-inverse-sampler \
  --opt-cmake-flags "-DG4GPU_BD001_MOLLER_BHABHA=ON" \
  --workload W1 \
  --physics-list PL1 PL2 PL3 PL4 \
  --hw H3 \
  --n-seeds 5 \
  --dry-run
```

Rationale: `W1` (`gamma_100mev`) is the existing EM-shower harness workload most
likely to exercise electron/positron delta-ray production without requiring the
methodology-blocked W5/W6 full-event drivers. Later paper-grade runs should use
20 seeds and add any true NNBAR full-event workload only after the W5/W6 driver
preflight gate is resolved.

## Exact prerequisites

1. Create an optimized branch, suggested name
   `lane/bd-geant4-001-moller-bhabha-inverse-sampler`, rooted in the intended
   Geant4/G4GPU integration branch.
2. Add `benchmarks/optimizations_registry.yaml` entry:
   `BD-geant4-001`, branch, CMake flag, description, and dependency list.
3. Implement the sampler behind an off-by-default flag plus strict fallback to
   the vanilla rejection sampler for compatibility and parity debugging.
4. Add unit/distribution tests over both Moller and Bhabha branches: sampled
   `x`, delta-ray energy, angular downstream observables, and rejection/fallback
   boundary cases.
5. Run only dry-run harness command-shape checks until the branch, registry,
   unit tests, and reference manifest are present; then request a guarded SLURM
   smoke before any `benchmarks/results/results.parquet` row is appended.
6. Keep `BD-geant4-001` database status `OPEN` until a terminal harness result
   row exists with `parity_pass=true` or an explicit `PARITY_FAIL` disposition.

No SLURM submit/cancel/dry-run via `sbatch`, event execution, result-row append,
reference regeneration, NNBAR production edit, speedup claim, or parity claim was
performed by this triage.
