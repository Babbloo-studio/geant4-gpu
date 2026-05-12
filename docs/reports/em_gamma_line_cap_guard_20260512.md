# EM/gamma line-cap guard (2026-05-12)

## Scope

This never-idle gap-scan guard keeps the compact EM/gamma scaffold, verifier
scripts, SLURM wrapper, and CMake wiring under the shared ≤500-line cap. It is
an evidence-maintenance guard only; it does not implement photoelectric, pair,
or bremsstrahlung physics.

## Guarded paths

`CMakeLists.txt`, `include/g4gpu/EMStepKernel.hh`,
`src/physics/EMStepKernel.cu`, `tests/test_em_klein_nishina.cu`,
`slurm/em_gamma_runtime_gate.sbatch`, and all current
`scripts/verify_em_gamma_*.py` verifier scripts are checked by
`scripts/verify_em_gamma_line_caps.py`; the inventory is also covered by `scripts/verify_em_gamma_report_coverage.py`.

## Boundary

No SLURM submission, detector/event workload, reference generation, result row,
or production output mutation is authorized by this guard. It makes no speedup, parity, or readiness claim; deferred EM process implementations remain blocked
by their existing fail-closed contracts.
