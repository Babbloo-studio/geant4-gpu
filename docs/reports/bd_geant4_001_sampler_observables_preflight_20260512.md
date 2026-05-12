# BD-geant4-001 sampler-observable preflight (2026-05-12)

Scope: one compact fail-closed prerequisite after the registry-row preflight for
`BD-geant4-001`. This does not implement the Moller/Bhabha inverse sampler,
submit SLURM, run events, regenerate references, append a result row, promote
parity/speedup, or edit NNBAR production code.

## Selected triage blocker

Chosen slice: sampler-specific validation observables.

The triage report requires distribution-level checks for sampled `x`, delta-ray
kinetic energy, angle, and downstream energy loss before any BD-001 speedup row
is trusted. The existing event-level parity gate is deliberately unchanged;
this iteration adds a separate BD-001 gate that future sampler validation output
must satisfy.

## Implementation

- Added `benchmarks/harness/sampler_observables.py` with
  `bd001_sampler_observable_gate(...)`.
- Required BD-001 observables:
  - `sampler_x`
  - `delta_ray_ke_mev`
  - `delta_ray_theta_rad`
  - `downstream_dedx_mev_mm`
- Missing, empty, non-numeric, null-only, or non-finite columns fail closed via
  `SamplerObservableError`; no observable is silently skipped.
- The gate runs two-sample KS tests and reports per-observable p-values plus a
  fail list without writing `benchmarks/results/results.parquet`.
- Added focused tests in
  `benchmarks/harness/tests/test_sampler_observables.py` for identical-pass,
  shifted-fail, alias resolution, and missing-column fail-closed behavior.
- Exported the helper from `benchmarks.harness` and registered CTest target
  `g4gpu_benchmark_harness_sampler_observables`.

## BD-001 disposition

`BD-geant4-001` remains blocked for measurement. This preflight only proves that
future sampler-validation Parquet artifacts can be checked with a stricter
sampler-level gate. Remaining blockers include an optimized sampler branch or
approved adapter, optimized Geant4 source/prefix selection, a real reviewed
registry row, physics-list selector proof, a guarded dry-run, and only then any
SLURM measurement/result-row work.

## Verification

Commands run in `/projects/hep/fs10/shared/nnbar/billy/geant4-gpu`:

```bash
python -m py_compile benchmarks/harness/sampler_observables.py benchmarks/harness/tests/test_sampler_observables.py
python benchmarks/harness/tests/test_sampler_observables.py
python scripts/verify_bd001_sampler_observables_preflight.py
git diff --check -- CMakeLists.txt benchmarks/harness/sampler_observables.py benchmarks/harness/tests/test_sampler_observables.py benchmarks/harness/__init__.py docs/reports/bd_geant4_001_sampler_observables_preflight_20260512.md scripts/verify_bd001_sampler_observables_preflight.py
```

Observed direct test terminator: `benchmark_harness_sampler_observables: PASS`.
Observed verifier terminator: `BD001_SAMPLER_OBSERVABLES_PREFLIGHT_OK`.

## Explicit non-actions

No SLURM submission, no holder-node event run, no reference regeneration, no
`benchmarks/results/results.parquet` row, no parity/speedup promotion, no
Moller/Bhabha sampler implementation, and no NNBAR production edit were
performed.
