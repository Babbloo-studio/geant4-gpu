# BD-geant4-001 L1-to-harness triage

Date: 2026-05-12
Lane: g4gpu-phase5 lane-swap by PANE 2 (`g4gpu-em-gamma-kernel` never-idle)
Status: BLOCKED at L1; no implementation branch or measured harness row exists.

## Bottleneck subject

`BD-geant4-001` is the Moller/Bhabha delta-ray sampler entry from the
Geant4 bottleneck database.  The source anchor is Geant4 v11.2.2
`source/processes/electromagnetic/standard/src/G4MollerBhabhaModel.cc`, lines
296--349: both the electron and positron branches use `flatArray(2, rndm)`, a
rational proposal for `x`, a scalar differential-cross-section weight `z`, and
an accept/reject loop.

The proposed optimization target remains:

- optimization id: `BD-geant4-001`
- implementation branch: `g4-em-moller-bhabha-inverse-sampler`
- intended CMake toggle: `-DG4EM_MOLLER_BHABHA_INVERSE_SAMPLER=ON`
- claim level before measurement: `L1` only (`Predicted` in
  `docs/specs/paper-methodology.md`)

## Current branch/prototype probe

Local branch and source probes found no implementation branch or prototype to
hand to the harness:

- `git -C /projects/hep/fs10/shared/nnbar/billy/geant4-gpu branch -a --list
  '*BD*' '*bd*' '*moller*' '*bhabha*' '*inverse*'` returned no matching
  branch.
- `git -C /projects/hep/fs10/shared/nnbar/billy/geant4-fork branch -a --list
  '*BD*' '*bd*' '*moller*' '*bhabha*' '*inverse*'` returned no matching
  branch.
- Recursive source grep found only upstream/reference `G4MollerBhabhaModel`
  occurrences and no `BD-geant4-001`, inverse-sampler, or
  `g4-em-moller-bhabha-inverse-sampler` implementation marker.

Therefore this triage must not append `benchmarks/results/results.parquet`,
submit SLURM, or claim speedup/parity.

## Harness dry-run shape after implementation exists

Once the branch exists and is checked out/built through the harness builder,
the bounded first dry-run command is:

```bash
/projects/hep/fs10/shared/nnbar/billy/packages/hibeam_env/bin/python \
  -m benchmarks.harness.run \
  --opt-id BD-geant4-001 \
  --opt-branch g4-em-moller-bhabha-inverse-sampler \
  --opt-cmake-flags=-DG4EM_MOLLER_BHABHA_INVERSE_SAMPLER=ON \
  --workload W1 \
  --physics-list PL1 \
  --hw H3 \
  --n-seeds 5 \
  --dry-run
```

This command was executed only in dry-run mode in the current G4GPU checkout.
It rendered an sbatch script named `g4gpu-BD-geant4-001-W1` with H3/`lu48`
settings, W1/PL1 paths, five seeds (`1001`--`1005`), a vanilla binary path, and
an optimized binary path under `benchmarks/builds/optimized/BD-geant4-001/W1`.
Because dry-run rendering does not prove that the target branch or optimized
binary exists, it is recorded as command-shape evidence only.

## Exact blockers before any measured row

OPEN: implementation_branch_missing — create or import the
`g4-em-moller-bhabha-inverse-sampler` Geant4 implementation branch.  The branch
must preserve the old rejection sampler as the strict-compatibility fallback and
must expose the optimization through an explicit build/runtime knob.

OPEN: builder_source_ref_missing — run the harness builder against the optimized
source so `build_optimized(..., verify_ref=True)` resolves the branch and writes
a clean build log.  The dry-run command above is insufficient because it does
not verify the branch or binary.

OPEN: sampler_unit_validation_missing — add a deterministic sampler-level test
covering electron and positron branches across `(gamma, xmin, xmax)` bins.  The
new sampler must pass KS/AD distribution checks for sampled `x` and must document
whether it is bit-exact fallback only or statistically equivalent optimized
mode.

OPEN: workload_matrix_missing — after sampler validation, run a guarded harness
measurement beginning with W1/PL1/H3 only.  Promotion beyond L2 requires the
paper-methodology matrix: W1+W2 with PL1+PL2, 20 seeds, parity p-values > 0.05,
hardware evidence, and append-only harness rows.

OPEN: parity_and_claim_gate_missing — no result tag (`SPEEDUP`, `NEUTRAL`,
`REGRESSION`, or `PARITY_FAIL`) may be assigned until the harness collector has
written a row with seed list, wall times, KS p-values, hardware evidence, and the
optimized commit hash.

## Boundaries observed in this triage

- No SLURM submission, `sbatch --test-only`, event execution, reference
  regeneration, or result-row write was performed.
- No NNBAR production code/data was edited.
- No parity, speedup, or paper-ready claim is made.
