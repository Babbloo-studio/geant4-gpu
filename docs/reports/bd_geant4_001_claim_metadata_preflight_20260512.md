# BD-geant4-001 claim-metadata harness preflight (2026-05-12)

Scope: one compact fail-closed preflight for moving `BD-geant4-001` toward the
Phase 5 benchmark harness. This does not implement the Moller/Bhabha sampler,
submit SLURM, run events, regenerate references, append result rows, edit NNBAR
production code, or claim parity/speedup.

## Selected triage blocker

Chosen slice: claim-level / Geant4-version / notes propagation from
`benchmarks.harness.run` into generated runner scripts and compute-node collect
metadata.

The earlier triage found that `run.py` accepted `--claim-level`,
`--geant4-version`, and `--notes`, while the dry-run planning path constructed
`RunnerSpec` without those fields. A BD-001 L2/L3 dry run could therefore print
a script with default `CLAIM_LEVEL=L0`, weakening later result provenance.

## Implementation

- `benchmarks/harness/run.py` now passes `claim_level`, `geant4_version`, and
  `notes` into each `RunnerSpec` created by `_plan_scripts(...)`.
- `run.py` validates claim metadata before script rendering:
  - `--claim-level` must be one of the schema-defined levels;
  - L3 rows remain fail-closed if `--notes` is non-empty;
  - `--geant4-version` must be non-empty.
- `benchmarks/harness/tests/test_run.py` covers BD-001 dry-run script metadata
  and invalid-claim fail-closed paths. The generated script now contains the
  requested `CLAIM_LEVEL`, `GEANT4_VERSION`, and `NOTES` variables and forwards
  them to the compute-node `--collect` command.

## Verification

Commands run in `/projects/hep/fs10/shared/nnbar/billy/geant4-gpu`:

```bash
PY=/projects/hep/fs10/shared/nnbar/billy/packages/hibeam_env/bin/python
$PY -m py_compile benchmarks/harness/*.py
$PY benchmarks/harness/tests/test_run.py
$PY -m pytest benchmarks/harness/tests/test_run.py benchmarks/harness/tests/test_runner.py -q
ctest --test-dir build --output-on-failure -R 'g4gpu_benchmark_harness_(run|runner)'
git diff --check
```

Observed results: direct `test_run.py` printed `benchmark_harness_run: PASS`,
pytest passed `21 passed`, focused CTest passed `2/2`, and `git diff --check`
passed.

## Remaining BD-001 blockers

`BD-geant4-001` remains fail-closed. Still required before any harness result:

1. optimized Moller/Bhabha sampler branch or approved isolated adapter;
2. optimized Geant4 source/prefix selection in the builder or equivalent proof;
3. `benchmarks/optimizations_registry.yaml` entry for `BD-geant4-001`;
4. sampler-specific validation observables for `x`, delta-ray kinetic energy,
   angle, and downstream energy loss;
5. physics-list selector proof for W1/W2 PL1/PL2;
6. guarded SLURM smoke only after the dry-run/script audits above are complete.
