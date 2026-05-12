# EM/gamma option-OFF configure gate — 2026-05-12

## Scope

This report records a live configure/build gate for `G4GPU_WITH_EM=OFF`. It is
limited to the isolated G4GPU repository and does not submit SLURM, run detector
events, generate benchmark rows, or claim physics parity.

## Required evidence

The verifier `scripts/verify_em_gamma_option_off_config.py` configures a
separate temporary build tree with `G4GPU_WITH_EM=OFF`,
`G4GPU_WITH_OPTICAL=OFF`, and `G4GPU_WITH_RTX=OFF`; builds only the `G4GPU`
library target; inspects `ctest -N` plus build-target help output; and removes
the temporary tree when the check exits.

The gate fails if the OFF build exposes any `g4gpu_em_*` CTest target, the
standalone `test_em_klein_nishina` target, or an ON-valued `G4GPU_WITH_EM` cache
entry. This complements the static option-boundary parser by checking CMake's
actual generated build tree.

## Boundary

Passing this gate proves only that the EM/gamma scaffold is disabled by the CMake
option in a clean OFF configure. It does not implement deferred EM processes,
does not authorize SLURM submission, and does not make speedup, parity, or
production-readiness claims.
