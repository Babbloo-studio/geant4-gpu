# EM/gamma verifier-script boundary audit — 2026-05-12

## Scope

This audit guards the EM/gamma Python verifier scripts themselves. It is a
static verifier-only gate: no kernel runtime path, physics table, secondary
buffer, detector/event workload, benchmark result row, SLURM job, or production
output is changed here.

## Verifier-script contract

Normal `g4gpu_em_*` CTest verifier scripts may read source, reports, CMake, and
published fallback artifacts. They must not submit jobs, launch production
workloads, mutate benchmark or detector outputs, delete files, or generate
Parquet/result rows. The one strict runtime-gate script remains manual and
fail-closed; normal CTest covers its text and archived GPU report rather than
using it to request an allocation.

## Boundary

Passing `g4gpu_em_verifier_script_boundary` only proves that EM/gamma Python
verifier scripts avoid known mutation and submission call shapes. It does not
authorize SLURM submission, detector or event-driver execution, output-row
generation, reference regeneration, physics-parity claims, speedup claims, ABI
migration, or executable photoelectric, pair-production, or bremsstrahlung
implementation.
