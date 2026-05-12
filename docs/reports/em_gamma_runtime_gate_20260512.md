# EM/gamma runtime GPU gate

Date: 2026-05-12
Checkout: `/projects/hep/fs10/shared/nnbar/billy/geant4-gpu-em-gamma`
Branch: `lane/g4gpu-em-gamma`

## Purpose

The EM/gamma scaffold already has compile-only evidence and an explicit
deferred GPU runtime test. This compact audit hardens that boundary: a login
node or CPU-only environment must not be mistaken for a passed Klein-Nishina
runtime validation.

## Changes

- `tests/test_em_klein_nishina.cu` now exits with code `77` when no CUDA device
  is visible, while still printing the existing `SKIP:` marker.
- `CMakeLists.txt` marks `g4gpu_em_klein_nishina` with `SKIP_RETURN_CODE 77`,
  so CTest records no-device execution as skipped rather than as a physics pass.
- `CMakeLists.txt` also sets build RPATHs to the discovered CUDA target library
  directory for `G4GPU` and the EM test, preventing missing-`libcudart.so.12`
  loader failures from masquerading as physics-test failures.
- `scripts/verify_em_gamma_runtime_gate.py` is a fail-closed GPU-node verifier:
  it succeeds only when the built executable exits zero and prints
  `PASS: Klein-Nishina scattered-energy KS`.

## Prompt-to-artifact checklist

| Requirement | Evidence | Status |
|-------------|----------|--------|
| Preserve scaffold boundary | No photoelectric, pair-production, or bremsstrahlung implementation added | PASS |
| Prevent no-GPU green proxy | Test returns `77` on CUDA-unavailable path and CTest has `SKIP_RETURN_CODE 77` | PASS |
| Keep runtime loader path explicit | Build RPATH includes the discovered CUDA target library directory | PASS |
| Provide real runtime gate | `scripts/verify_em_gamma_runtime_gate.py` requires the PASS marker and rejects `SKIP` | PASS |
| Keep file caps | CMake/test/script/report remain below 500 lines | PASS |
| Preserve isolation | G4GPU-only files touched; no NNBAR production code/data dependency added | PASS |

## Verification boundary

This iteration does not submit SLURM and does not claim a GPU runtime pass. The
expected login-node outcome for the new verifier is fail-closed:
`EM_GAMMA_RUNTIME_GATE_BLOCKED` if no CUDA device is visible. A future approved
GPU-node goal should rerun the verifier and archive an `EM_GAMMA_RUNTIME_GATE_OK`
transcript before promoting runtime validation.

Observed local verification:

```text
cmake --build build --target G4GPU test_em_klein_nishina -j2
  Built target G4GPU
  Built target test_em_klein_nishina

ctest --test-dir build --output-on-failure -R '^g4gpu_em_klein_nishina$'
  g4gpu_em_klein_nishina ... Skipped
  100% tests passed, 0 tests failed out of 1
  The following tests did not run: g4gpu_em_klein_nishina (Skipped)

./scripts/verify_em_gamma_runtime_gate.py
  SKIP: CUDA device unavailable for Klein-Nishina runtime test
  EM_GAMMA_RUNTIME_GATE_BLOCKED: rerun on an allocated GPU node
```
