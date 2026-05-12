# EM/gamma preflight contract index — 2026-05-12

## Scope

This index lists the shared fail-closed preflight contracts that must be green
before the deferred EM/gamma processes can move from documentation stubs to
executable GPU physics. It is documentation/verifier coverage only: no kernel
runtime path is changed, no physics table or secondary buffer is allocated, and
no photoelectric, pair-production, or bremsstrahlung physics is implemented.

## Required shared preflights

| Order | Contract | Artifact | Blocks |
|---:|---|---|---|
| 1 | Table owner | `docs/reports/em_gamma_table_owner_preflight_20260512.md` | material/energy cross-section ownership and missing-table gates |
| 2 | Secondary buffer | `docs/reports/em_gamma_secondary_buffer_preflight_20260512.md` | pair-production and bremsstrahlung secondary emission |
| 3 | RNG stream | `docs/reports/em_gamma_rng_stream_preflight_20260512.md` | reproducible process competition and bounded stochastic sampling |
| 4 | Process selector | `docs/reports/em_gamma_process_selector_preflight_20260512.md` | material/energy competition between photoelectric, Compton, pair production, and bremsstrahlung |
| 5 | Status code vocabulary | `docs/reports/em_gamma_status_code_preflight_20260512.md` | named fail-closed host-visible status counters and ABI migration |

## Invariants

- `SampleCompton` remains the only executable EM process in the current kernel.
- `SamplePhotoelectric`, `SamplePair`, and `SampleBremsstrahlung` remain
  fail-closed stubs until their process-specific implementation and validation
  contracts are updated in the same commit as any behavior change.
- Each shared preflight must have a Python verifier, a CTest target, and static
  contract coverage so missing registration fails locally before any GPU run.
- Passing this index does not imply Geant4 parity, detector/event validation,
  speedup, paper-ready results, or permission to append benchmark rows.

## Boundary

This preflight index does not authorize SLURM submission, detector or
event-driver execution, output-row generation, reference regeneration,
physics-parity claims, speedup claims, ABI migration, or use of NNBAR production
code/data.
