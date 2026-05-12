# BD-geant4-001 implementation branch gate preflight

Date: 2026-05-12
Lane: `g4gpu-phase5-bd001-implementation-branch-gate` (PANE 3 lane-swap)
Scope: compact fail-closed harness prerequisite only. No SLURM submission,
event execution, reference regeneration, result-row write, parity/speedup
promotion, optimized Moller/Bhabha sampler implementation, or NNBAR production
edit was performed.

## Prompt-to-artifact mapping

| Requirement | Evidence / disposition |
|---|---|
| Add a prerequisite for a real BD001 optimized sampler branch or registry-row gate after source-prefix preflight | Added `benchmarks/harness/bd001_branch_gate.py`. |
| Fail closed until a real branch/source anchor exists | The gate requires a BD-geant4-001 registry row, `optimized_geant4_prefix`, a git source repo, a resolvable registry branch/ref, the Geant4 source target `G4MollerBhabhaModel.cc` at that ref, a BD001/Moller/Bhabha CMake flag marker in that source, and the fallback rejection-sampler token `flatArray(2, rndm)`. |
| Avoid mutation and measurements | The gate uses read-only `git rev-parse`/`cat-file`; it does not checkout, build, submit, run, collect, or write results. |
| Make it testable | Added focused fixture tests and CMake registration `g4gpu_benchmark_harness_bd001_branch_gate`. |

## Verification

- `python -m py_compile benchmarks/harness/bd001_branch_gate.py benchmarks/harness/tests/test_bd001_branch_gate.py benchmarks/harness/__init__.py`
- `python benchmarks/harness/tests/test_bd001_branch_gate.py` -> `benchmark_harness_bd001_branch_gate: PASS`
- `python -m pytest benchmarks/harness/tests/test_bd001_branch_gate.py -q` -> `3 passed`
- `python -m pytest benchmarks/harness/tests -q` -> `53 passed`
- Existing focused CTest subset still passes for run/runner/optimization-registry (`3/3`).
- Static CMake registration grep finds `g4gpu_benchmark_harness_bd001_branch_gate`.
- A CMake refresh was attempted for the new CTest registration but the existing build environment failed before generation with a compiler-feature metadata error unrelated to this Python-only gate; no build, event run, or SLURM action was performed.

## Remaining BD-001 blockers

BD-geant4-001 remains blocked on an actual optimized Moller/Bhabha sampler
branch/install prefix, a reviewed production registry row, driver-side
physics-list implementation evidence, guarded smoke, and only then any
measurement row.
