# EM/gamma GPU runtime gate — job 3049900

## Scope

This report records the first GPU-node execution of the EM/gamma
Klein-Nishina runtime gate after the guarded wrapper was committed at
`c4ab69d3566f6003f3e1f86817ece1ba6b488545` (`test(em): add guarded runtime
sbatch`). The job ran on 2026-05-12 on LUNARC `gpua40i` node `cg15`.

This is a Compton-sampling runtime validation only. It does not implement or
validate photoelectric, pair-production, or bremsstrahlung physics, does not run
a detector/event workload, does not mutate production output, and does not claim
physics parity or speedup.

## Submission and accounting

- Duplicate check: no active `g4gpu-em-rtgate` job was listed before submission.
- Syntax/preflight: `EM_GAMMA_RUNTIME_APPROVED=YES sbatch --test-only
  slurm/em_gamma_runtime_gate.sbatch` returned pseudo job `3049899` scheduled on
  `cg15`.
- Real submission: `EM_GAMMA_RUNTIME_APPROVED=YES sbatch --parsable
  slurm/em_gamma_runtime_gate.sbatch` returned job `3049900`.
- Accounting artifact: `docs/reports/em_gamma_runtime_gate_gpu_3049900_sacct.txt`
  records `COMPLETED`, exit code `0:0`, elapsed `00:00:27`, node `cg15`, and
  one `gres/gpu=1` allocation.

## Runtime evidence

The Slurm wrapper configured and rebuilt the current checkout on the GPU node,
then ran both the CTest and fail-closed runtime verifier.

| Evidence | Artifact | Result |
| --- | --- | --- |
| CTest runtime | `docs/reports/em_gamma_runtime_gate_gpu_3049900_ctest.txt` | `g4gpu_em_klein_nishina` passed 1/1 and printed `PASS: Klein-Nishina scattered-energy KS p=0.166506 D=0.0111339 samples=10000`. |
| Strict runtime gate | `docs/reports/em_gamma_runtime_gate_gpu_3049900_gate.txt` | Printed the same KS PASS marker plus `EM_GAMMA_RUNTIME_GATE_OK`. |
| Wrapper success | `slurm/em-gamma-runtime-3049900.out` | Ends with `EM_GAMMA_RUNTIME_SLURM_OK job=3049900`. |

## Remaining blocked work

1. Keep photoelectric, pair-production, and bremsstrahlung stubs fail-closed
   until explicit physics-table, secondary-buffer, process-selection, and
   per-process validation contracts exist.
2. Do not promote detector-level parity or performance claims from this unit;
   the evidence is limited to the standalone 1 MeV gamma Klein-Nishina sampler.
3. If later commits change the EM kernel, rerun the guarded GPU runtime gate and
   archive a new job-specific report rather than reusing job `3049900`.
