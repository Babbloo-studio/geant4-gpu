# EM/gamma CTest execution-boundary audit — 2026-05-12

## Scope

This audit locks the current EM/gamma CTest command boundary. It is a
fail-closed documentation and verifier artifact only: no kernel runtime path,
physics table, secondary buffer, benchmark executable, detector/event workload,
SLURM job, or output row is changed by this audit.

The allowed EM/gamma CTest surface is intentionally narrow:

| Class | Allowed command shape | Current purpose |
|---|---|---|
| Standalone sampler fixture | `g4gpu_em_klein_nishina` executes only `tests/test_em_klein_nishina` and keeps `SKIP_RETURN_CODE 77` for no-GPU holder contexts. | Compton Klein-Nishina runtime fixture already archived separately by the GPU runtime-gate report. |
| Static/fail-closed verifiers | Every other `g4gpu_em_*` CTest target executes `${Python3_EXECUTABLE}` plus one `scripts/verify_em_gamma_*.py` verifier. | Contract, preflight, publication, and boundary checks that must not launch production workloads. |

## Explicit non-goals

The EM/gamma CTest block is not a benchmark-result producer, paper-output
producer, detector/event runner, reference-regeneration path, or SLURM launcher.
It must not call benchmark executables, write Parquet result rows, invoke
`sbatch`/`srun` as a CTest command, or read NNBAR production code/data.

The guarded runtime wrapper remains outside the CTest execution path: CTest may
verify the wrapper text with `verify_em_gamma_runtime_sbatch.py`, but it must not
submit the wrapper. Future GPU runtime evidence must stay an explicitly approved
allocation artifact with archived logs and a separate report.

## Current blocker state

This audit does not remove any deferred EM physics blocker. The following remain
open before executable photoelectric, pair-production, or bremsstrahlung physics
or any publication claim:

- No `G4GPUEMPhysicsTables` implementation exists.
- No `G4GPUEMSecondaryBuffer` implementation exists.
- No `G4GPUEMRngStream`, `G4GPUEMProcessSelector`, or `G4GPUEMStatusCode`
  implementation exists.
- No photoelectric, pair-production, or bremsstrahlung GPU validation fixture has
  been generated.
- No detector/event workload, benchmark result row, physics-parity claim, or
  speedup claim is authorized by this audit.

## Boundary

Passing `g4gpu_em_ctest_execution_boundary` only proves that the EM-labelled
CTest commands remain local, static/fail-closed, and non-production shaped. It
does not authorize SLURM submission, detector or event-driver execution,
output-row generation, reference regeneration, physics-parity claims, speedup
claims, ABI migration, or use of NNBAR production code/data.
