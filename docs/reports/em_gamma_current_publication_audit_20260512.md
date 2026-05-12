# EM/gamma current-publication audit — 2026-05-12

## Scope

This never-idle audit updates the evidence map for the EM/gamma compact unit at
current local head `005e194f73668107e56a6f3a8bc0818c3aa978dc`
(`test(em): guard deferred stubs fail closed`). The original fork-published
head remains `75660c2`; later hardening commits are fallback-published as local
bundles because HTTPS push is credential-blocked.

No SLURM command, GPU runtime test, detector/event run, reference generation,
NNBAR production edit, parity claim, or speedup claim was performed by this
audit.

## Prompt-to-artifact checklist

| Requirement / gate | Current evidence | Status |
| --- | --- | --- |
| EM/gamma scaffold is present | `include/g4gpu/EMStepKernel.hh`, `src/physics/EMStepKernel.cu`, and `tests/test_em_klein_nishina.cu` remain in the `lane/g4gpu-em-gamma` tree. | PASS |
| Runtime gate refuses no-GPU evidence | `scripts/verify_em_gamma_runtime_gate.py` exits `2` with `EM_GAMMA_RUNTIME_GATE_BLOCKED` when the Klein-Nishina test skips for no visible CUDA device. | PASS |
| Deferred processes remain explicit blockers | `docs/reports/em_gamma_deferred_process_gap_audit_20260512.md` plus `scripts/verify_em_gamma_deferred_process_gap.py` keep photoelectric, pair-production, and bremsstrahlung blocked on missing physics-table, secondary-buffer, process-selection, and per-process validation contracts. | PASS |
| Static contract is checked | `scripts/verify_em_gamma_static_contract.py` requires the header/API markers, Compton sampler, CMake wiring, and EM CTest registrations. | PASS |
| Deferred stubs are fail-closed | `scripts/verify_em_gamma_stub_fail_closed.py` checks the three deferred stubs keep `out = {};`, TODO markers, `return;`, and no mutation hooks until real contracts exist. | PASS |
| Current fallback publication exists | `/projects/hep/fs10/shared/nnbar/billy/g4gpu-em-gamma-publication/lane-g4gpu-em-gamma-005e194.bundle`, `patches/0008-em-gamma-stub-fail-closed-005e194.patch`, `BUNDLE_VERIFY_005e194.txt`, and `SHA256SUMS-005e194-stub-fail-closed` exist. | PASS |
| Current verifier covers hardening chain | `check_em_gamma_current_005e194.latest.txt` ends `EM_GAMMA_CURRENT_005E194_OK` after checksum checks through `e7cf78f`, `122e239`, `589a11a`, `7acb856`, `087e8ca`, and `005e194`. | PASS |
| No isolation leak | Current verifier transcript contains `ISOLATION_OK`; the source-side grep covers G4GPU `include`, `src`, and `tests`. | PASS |
| No false GPU physics claim | Transcript records the expected no-GPU runtime-gate result: `runtime_gate_rc=2` and `EM_GAMMA_RUNTIME_GATE_BLOCKED`. | PASS |

## Live evidence snapshot

```text
branch=lane/g4gpu-em-gamma
head=005e194f73668107e56a6f3a8bc0818c3aa978dc
subject=test(em): guard deferred stubs fail closed
EM_GAMMA_STATIC_CONTRACT_OK
EM_GAMMA_DEFERRED_PROCESS_GAP_OK
EM_GAMMA_STUB_FAIL_CLOSED_OK
focused deferred/static/stub CTest: 3/3 passed
runtime_gate_rc=2
EM_GAMMA_CURRENT_005E194_OK
```

Line-count evidence from the current verifier keeps all touched EM files below
the 500-line cap: `CMakeLists.txt` 193, `EMStepKernel.hh` 109,
`EMStepKernel.cu` 255, `test_em_klein_nishina.cu` 166, runtime verifier 90,
deferred verifier 86, static verifier 93, stub verifier 97, and deferred report
69 lines.

## Remaining blocked work

1. Run `g4gpu_em_klein_nishina` on an allocated GPU node and require the KS
   `PASS` marker before counting any runtime Compton-sampling evidence.
2. Design and validate explicit contracts for photoelectric, pair-production,
   and bremsstrahlung before changing their fail-closed stubs.
3. Refresh GitHub publication only when credentials are available; until then,
   the authoritative transport path for commits after `75660c2` is the fallback
   bundle/patch/checksum set in `g4gpu-em-gamma-publication`.
