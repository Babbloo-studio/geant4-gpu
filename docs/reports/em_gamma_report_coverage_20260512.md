# EM/gamma report-coverage audit — 2026-05-12

## Scope

This audit locks the documentation-to-verifier coverage map for the current
EM/gamma lane. It is a static coverage artifact only: no kernel runtime path,
physics table, secondary buffer, detector/event workload, benchmark result row,
SLURM job, or production output is changed here.

Every `docs/reports/em_gamma_*_20260512.md` markdown report must be explicitly
classified as one of the following:

| Coverage class | Requirement |
|---|---|
| CTest verifier | A `scripts/verify_em_gamma_*.py` verifier exists and is registered as a `g4gpu_em_*` CTest target. |
| Shared static verifier | The report is intentionally covered by `verify_em_gamma_static_contract.py` plus an EM CTest target because it audits the original scaffold rather than a later standalone contract. |
| Manual fail-closed gate | The report owns a fail-closed script that is intentionally not a normal CTest target because it requires an approved GPU allocation to pass. |

## Current coverage rules

- Per-process contracts, preflight contracts, indexes, publication audits,
  runtime GPU evidence, and boundary audits are CTest-verifier covered.
- The original kernel-completion audit remains covered by the shared static
  contract and source-boundary CTests rather than a new duplicate verifier.
- The strict runtime gate script remains manual/fail-closed and must stay out of
  the normal EM CTest set; the archived GPU runtime report is separately covered
  by `g4gpu_em_runtime_gpu_report`.

## Boundary

Passing `g4gpu_em_report_coverage` only proves that EM/gamma markdown reports
are inventoried and tied to an explicit verifier class. It does not authorize
SLURM submission, detector or event-driver execution, output-row generation,
reference regeneration, physics-parity claims, speedup claims, ABI migration, or
use of NNBAR production code/data.
