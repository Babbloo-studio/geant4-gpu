# EM/gamma preflight-chain audit — 2026-05-12

## Scope

This audit records the current fail-closed EM/gamma preflight chain at G4GPU
head `07912d0` (`docs(em): index shared preflight contracts`). It is an audit
artifact only: no kernel runtime path is changed, no physics table or secondary
buffer is allocated, and no photoelectric, pair-production, or bremsstrahlung
physics is implemented.

## Prompt-to-artifact checklist

| Requirement | Evidence |
|---|---|
| EM kernel scaffold remains present | `include/g4gpu/EMStepKernel.hh`, `src/physics/EMStepKernel.cu`, and `tests/test_em_klein_nishina.cu` are still checked by `g4gpu_em_static_contract`. |
| Only Compton is executable | `src/physics/EMStepKernel.cu` still dispatches gamma tracks to `SampleCompton`; `SamplePhotoelectric`, `SamplePair`, and `SampleBremsstrahlung` remain stub-gated by `g4gpu_em_stub_fail_closed`. |
| GPU runtime evidence exists for the scaffold | `docs/reports/em_gamma_runtime_gate_gpu_20260512.md` archives Slurm job `3049900` and strict `EM_GAMMA_RUNTIME_GATE_OK`; current no-GPU CTest may skip `g4gpu_em_klein_nishina`. |
| Per-process deferrals are explicit | `em_gamma_photoelectric_contract_20260512.md`, `em_gamma_pair_contract_20260512.md`, and `em_gamma_bremsstrahlung_contract_20260512.md` each have a verifier/CTest target. |
| Shared preflight chain is indexed | `docs/reports/em_gamma_preflight_contract_index_20260512.md` lists table owner, secondary buffer, RNG stream, process selector, and status-code vocabulary with verifier/CTest coverage. |
| Publication fallback exists | `/projects/hep/fs10/shared/nnbar/billy/g4gpu-em-gamma-publication/check_em_gamma_current_07912d0.sh` and `.latest.txt` end `EM_GAMMA_CURRENT_07912D0_OK`; bundle, patch, and checksum artifacts exist for `07912d0`. |
| Isolation boundary holds | The current verifier chain greps for forbidden NNBAR detector/reconstruction strings and the lane forbids NNBAR production code/data use. |

## Current blocker state

The current chain is complete as a fail-closed scaffold/preflight set, but the
following remain open before executable deferred EM physics or publication
claims:

- No `G4GPUEMPhysicsTables` implementation exists.
- No `G4GPUEMSecondaryBuffer` implementation exists.
- No `G4GPUEMRngStream`, `G4GPUEMProcessSelector`, or `G4GPUEMStatusCode`
  implementation exists.
- No photoelectric, pair-production, or bremsstrahlung GPU validation fixture has
  been generated.
- No detector/event workload, benchmark result row, physics-parity claim, or
  speedup claim is authorized by this audit.

## Boundary

This audit does not authorize SLURM submission, detector or event-driver
execution, output-row generation, reference regeneration, physics-parity claims,
speedup claims, ABI migration, or use of NNBAR production code/data.
