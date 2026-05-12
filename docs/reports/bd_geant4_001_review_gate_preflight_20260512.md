# BD-geant4-001 reviewed registry-row gate preflight

Date: 2026-05-12
Lane: `g4gpu-phase5-bd001-real-registry-row` (PANE 3 lane-swap)
Scope: compact fail-closed harness prerequisite only. No SLURM submission,
event execution, reference regeneration, result-row write, parity/speedup
promotion, optimized Moller/Bhabha sampler implementation, or NNBAR production
edit was performed.

## Prompt-to-artifact mapping

| Requirement | Evidence / disposition |
|---|---|
| Do one compact fail-closed prerequisite for a real reviewed BD001 registry row or explicit implementation-branch blocker | Added reviewed-registry metadata fields plus `benchmarks/harness/bd001_review_gate.py`. |
| Keep BD001 blocked until review evidence exists | The review gate composes the existing branch gate, then requires `review_status: approved`, at least one reviewer, `reviewed_commit` equal to the branch-gated commit, and an existing review artifact that names the opt id, branch, commit, approval, and reviewer tokens. |
| Avoid mutation and measurements | The gate is read-only; it does not checkout, build, submit, run, collect, append results, or create a real production registry row. |
| Make it testable | Added focused review-gate tests, optimization-registry shape tests for review metadata, and CMake registration `g4gpu_benchmark_harness_bd001_review_gate`. |

## Verification

- `python -m py_compile benchmarks/harness/optimization_registry.py benchmarks/harness/bd001_review_gate.py benchmarks/harness/tests/test_bd001_review_gate.py benchmarks/harness/tests/test_optimization_registry.py benchmarks/harness/__init__.py`
- `python benchmarks/harness/tests/test_bd001_review_gate.py` -> `benchmark_harness_bd001_review_gate: PASS`
- `python -m pytest benchmarks/harness/tests -q` -> `56 passed`.
- Static CMake registration grep finds `g4gpu_benchmark_harness_bd001_review_gate`.

## Remaining BD-001 blockers

BD-geant4-001 remains blocked on an actual optimized Moller/Bhabha sampler
branch/install prefix, a real approved review artifact/production registry row,
guarded smoke, and only then any measurement row.
