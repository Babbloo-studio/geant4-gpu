# EM/gamma lane-objective audit — 2026-05-12

## Scope

This audit maps the original `g4gpu-em-gamma-kernel` lane objective to the
current G4GPU artifacts. It is an evidence and verifier gate only: no kernel
runtime path, physics table, secondary buffer, detector/event workload,
benchmark result row, SLURM job, or production output is changed here.

## Prompt-to-artifact checklist

| Prompt requirement | Concrete evidence | Gate |
|---|---|---|
| Header interface exists under `include/g4gpu/EMStepKernel.hh` | The header declares `EMStep`, `LaunchEMStepKernel`, `LaunchComptonSampleKernel`, and the four process samplers. | `g4gpu_em_lane_objective_audit` plus `g4gpu_em_static_contract` |
| CUDA kernel source exists under `src/physics/EMStepKernel.cu` | The source contains the Kahn/Butcher-Messel Klein-Nishina sampler and keeps photoelectric, pair-production, and bremsstrahlung as documented TODO stubs. | `g4gpu_em_lane_objective_audit` plus `g4gpu_em_stub_fail_closed` |
| Klein-Nishina validation fixture exists | `tests/test_em_klein_nishina.cu` uses 10,000 samples, requires p-value above 0.05, and returns skip code 77 when no CUDA device is visible. | `g4gpu_em_lane_objective_audit` plus `g4gpu_em_klein_nishina` |
| CMake wiring is under `G4GPU_WITH_EM` | `CMakeLists.txt` adds `src/physics/EMStepKernel.cu`, links cuRAND, registers `g4gpu_em_klein_nishina`, and registers static/fail-closed audit CTests. | `g4gpu_em_lane_objective_audit` plus CTest listing |
| File-size cap is respected | Header, kernel, test, CMake, and EM verifier/report files remain below 500 lines. | `g4gpu_em_lane_objective_audit` |
| Isolation boundary is respected | EM source roots do not include or link NNBAR production code, and the NNBAR production pipeline is not invoked. | `g4gpu_em_source_boundary` |
| Runtime evidence is fail-closed and archived | Holder/no-GPU CTest may skip the fixture; GPU runtime evidence is archived separately in `em_gamma_runtime_gate_gpu_20260512.md`. | `g4gpu_em_runtime_gpu_report` |
| Current fallback publication is fresh | The current-head bundle, patch, verifier transcript, and checksum manifest are required by the dynamic artifact verifier. | `g4gpu_em_publication_artifacts` |
| Remaining EM processes are not falsely promoted | Photoelectric, pair-production, and bremsstrahlung stay blocked on table, secondary-buffer, selector/status, RNG, and validation-fixture contracts. | `g4gpu_em_deferred_process_gap` and contract/preflight CTests |

## Boundary

Passing `g4gpu_em_lane_objective_audit` only proves that the lane objective is
mapped to current artifacts and that the fail-closed boundaries remain explicit.
It does not authorize SLURM submission, detector or event-driver execution,
output-row generation, reference regeneration, physics-parity claims, speedup
claims, ABI migration, or executable photoelectric, pair-production, or
bremsstrahlung implementation.
