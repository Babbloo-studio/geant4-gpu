# EM/gamma claim-boundary audit — 2026-05-12

## Scope

This audit guards the language boundary for the EM/gamma lane. It is a static
claim-control gate only: no kernel runtime path, physics table, secondary
buffer, detector/event workload, benchmark result row, SLURM job, or production
output is changed here.

## Allowed claims

The lane may claim only the following current facts:

- The Compton Klein-Nishina scaffold and validation fixture exist.
- The archived GPU runtime gate passed for the standalone Klein-Nishina fixture.
- The remaining photoelectric, pair-production, and bremsstrahlung processes are
  deferred and fail-closed.
- Current fallback publication artifacts exist for the live head.

## Forbidden claims before future gates

The lane must not claim EM shower speedup, physics parity, paper readiness,
production readiness, detector/event validation, benchmark-result generation,
ABI migration, or completed executable photoelectric, pair-production, or
bremsstrahlung physics until separate reviewed gates add those artifacts.

## Boundary

Passing `g4gpu_em_claim_boundary` only proves that the current EM/gamma text
surfaces avoid known premature-claim phrases. It does not authorize SLURM
submission, detector or event-driver execution, output-row generation, reference
regeneration, physics-parity claims, speedup claims, ABI migration, or executable
photoelectric, pair-production, or bremsstrahlung implementation.
