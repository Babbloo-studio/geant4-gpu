# BD-geant4-001 optimization-registry preflight (2026-05-12)

Scope: one compact fail-closed prerequisite after the BD-001 claim-metadata
preflight. This does not implement the Moller/Bhabha sampler, create a real
registry row, submit SLURM, run events, regenerate references, append result
rows, edit NNBAR production code, or claim parity/speedup.

## Selected triage blocker

Chosen slice: `benchmarks/optimizations_registry.yaml` row validation for a
future `BD-geant4-001` entry.

The triage report requires a registry row before any dry-run or measurement is
trusted. Because no optimized BD-001 implementation branch exists yet, this
iteration adds validation machinery and fixture tests only; the real registry
file remains absent until a source owner provides a reviewed implementation
branch or approved adapter.

## Implementation

- Added `benchmarks/harness/optimization_registry.py` with:
  - `OptimizationRegistryEntry` typed metadata;
  - `load_registry(...)` and `require_entry(...)` fail-closed loaders;
  - validation for required `branch`, `cmake_flags`, `description`, and
    `depends_on` fields;
  - optional `claim_level` / `notes` checks reusing the harness schema claim
    levels, including the existing empty-notes rule for L3 rows;
  - unknown-field rejection so speedup/result evidence cannot be smuggled into
    registry metadata.
- Added `benchmarks/harness/tests/test_optimization_registry.py` with a valid
  fixture row for `BD-geant4-001`, missing-file/missing-entry blockers, and bad
  shape fail-closed cases.
- Exported the registry helper from `benchmarks/harness/__init__.py` and
  registered `g4gpu_benchmark_harness_optimization_registry` in CMake.

## Verification

Commands run in `/projects/hep/fs10/shared/nnbar/billy/geant4-gpu`:

```bash
PY=/projects/hep/fs10/shared/nnbar/billy/packages/hibeam_env/bin/python
$PY -m py_compile benchmarks/harness/*.py
$PY benchmarks/harness/tests/test_optimization_registry.py
$PY -m pytest benchmarks/harness/tests/test_optimization_registry.py -q
ctest --test-dir build --output-on-failure -R 'g4gpu_benchmark_harness_optimization_registry'
git diff --check
```

Observed results: direct registry test printed
`benchmark_harness_optimization_registry: PASS`, pytest passed `3 passed`,
focused CTest passed `1/1`, and `git diff --check` passed.

## Remaining BD-001 blockers

`BD-geant4-001` remains fail-closed. Still required before any harness result:

1. optimized Moller/Bhabha sampler branch or approved isolated adapter;
2. optimized Geant4 source/prefix selection in the builder or equivalent proof;
3. actual reviewed `benchmarks/optimizations_registry.yaml` row pinned to that
   implementation;
4. sampler-specific validation observables for `x`, delta-ray kinetic energy,
   angle, and downstream energy loss;
5. physics-list selector proof for W1/W2 PL1/PL2;
6. guarded SLURM smoke only after dry-run/script audits pass.
