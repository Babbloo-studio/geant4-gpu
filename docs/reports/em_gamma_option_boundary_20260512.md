# EM/gamma CMake option-boundary contract — 2026-05-12

## Scope

This report locks the `G4GPU_WITH_EM` build-option boundary for the EM/gamma
scaffold. It is a static contract only: it does not run a detector/event
workload, generate output rows, submit SLURM, or claim physics parity.

## Required boundary

The EM/gamma CUDA source, CTest targets, and standalone Klein-Nishina test must
remain guarded by `if(G4GPU_WITH_EM)` blocks in `CMakeLists.txt`.
Specifically, `src/physics/EMStepKernel.cu`, `test_em_klein_nishina`, and every
`g4gpu_em_*` CTest registration must be unreachable when `G4GPU_WITH_EM=OFF`.

The verifier `scripts/verify_em_gamma_option_boundary.py` parses CMake nesting
and fails closed if any EM marker escapes the option scope or if the boundary
report/test registration is removed.

## Boundary

Passing this gate proves only option-scope containment for the scaffold wiring.
It does not implement photoelectric, pair-production, or bremsstrahlung physics;
does not authorize SLURM submission; and does not make speedup, parity, or
production-readiness claims.
