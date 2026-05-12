# EM/gamma current-publication audit — 2026-05-12

## Scope

This never-idle audit records the historical evidence map for the EM/gamma compact
unit at audited subject head `ac6a00e1d9d31817eb064f292f2e7fda3f2a9d62`
(`docs(em): audit shared preflight chain`). The fork ref
`Babbloo-studio/geant4-gpu:lane/g4gpu-em-gamma` matched this head when the
audit was written; fallback bundle, patch, verifier transcript, and checksum
artifacts are also present under
`/projects/hep/fs10/shared/nnbar/billy/g4gpu-em-gamma-publication/`. Current-head
artifact freshness is delegated to `g4gpu_em_publication_artifacts`, which is
head-sensitive and must fail until each later commit has a fresh bundle, patch,
verifier transcript, and checksum manifest.

No new SLURM command, GPU runtime test, detector/event run, reference
generation, NNBAR production edit, parity claim, speedup claim, ABI migration,
or deferred-process implementation was performed by this audit.

## Prompt-to-artifact checklist

| Requirement / gate | Current evidence | Status |
| --- | --- | --- |
| EM/gamma scaffold is present | `include/g4gpu/EMStepKernel.hh`, `src/physics/EMStepKernel.cu`, and `tests/test_em_klein_nishina.cu` remain in the `lane/g4gpu-em-gamma` tree and are checked by `g4gpu_em_static_contract`. | PASS |
| Runtime gate has archived GPU evidence | `docs/reports/em_gamma_runtime_gate_gpu_20260512.md` archives Slurm job `3049900` with strict `EM_GAMMA_RUNTIME_GATE_OK`; current holder/no-GPU CTest may still skip `g4gpu_em_klein_nishina`. | PASS |
| Deferred stubs remain fail-closed | `scripts/verify_em_gamma_stub_fail_closed.py` checks `SamplePhotoelectric`, `SamplePair`, and `SampleBremsstrahlung` keep `out = {};`, TODO markers, `return;`, and no mutation hooks. | PASS |
| Shared preflights are indexed | `docs/reports/em_gamma_preflight_contract_index_20260512.md` indexes table owner, secondary buffer, RNG stream, process selector, and status-code vocabulary preflights. | PASS |
| Preflight chain has completion audit | `docs/reports/em_gamma_preflight_chain_audit_20260512.md` maps prompt requirements to concrete artifacts and keeps the remaining implementation blockers explicit. | PASS |
| Historical fallback publication exists | `lane-g4gpu-em-gamma-ac6a00e.bundle`, `patches/0019-em-gamma-preflight-chain-audit-ac6a00e.patch`, `BUNDLE_VERIFY_ac6a00e.txt`, and `SHA256SUMS-ac6a00e-preflight-chain-audit` exist in the publication directory. | PASS |
| Historical verifier covers the hardening chain | `check_em_gamma_current_ac6a00e.latest.txt` ends `EM_GAMMA_CURRENT_AC6A00E_OK` after direct preflight-chain/index/status/static verifiers, line caps, isolation grep, focused EM CTest, and `git diff --check`. | PASS |
| Current-head publication freshness | `g4gpu_em_publication_artifacts` now checks the live head dynamically and requires a fresh current-head bundle, patch, verifier transcript, and checksum manifest. | PASS |
| No isolation leak | The current verifier chain greps for forbidden NNBAR detector/reconstruction strings across the touched report/verifier/CMake and G4GPU `include`, `src`, and `tests` surfaces. | PASS |
| No false physics/performance claim | Reports and verifiers preserve explicit boundaries: no detector/event workload, output-row generation, physics-parity claim, speedup claim, ABI migration, or deferred-process implementation. | PASS |

## Live evidence snapshot

```text
branch=lane/g4gpu-em-gamma
head=ac6a00e1d9d31817eb064f292f2e7fda3f2a9d62
fork_ref=ac6a00e1d9d31817eb064f292f2e7fda3f2a9d62
subject=docs(em): audit shared preflight chain
EM_GAMMA_PREFLIGHT_CHAIN_AUDIT_OK
EM_GAMMA_PREFLIGHT_CONTRACT_INDEX_OK
EM_GAMMA_STATUS_CODE_PREFLIGHT_OK
EM_GAMMA_STATIC_CONTRACT_OK
focused EM CTest: 20/20 passed, with g4gpu_em_klein_nishina skipped on holder/no-GPU context
EM_GAMMA_CURRENT_AC6A00E_OK
```

Line-count evidence from the current verifier keeps all listed EM files below the
500-line cap: preflight-chain audit 42, preflight-chain verifier 107,
preflight-contract index 37, preflight-index verifier 112, static verifier 125,
CMakeLists 273, `EMStepKernel.hh` 109, `EMStepKernel.cu` 255, and
`test_em_klein_nishina.cu` 166 lines.

## Remaining blocked work

1. Implement and validate `G4GPUEMPhysicsTables`, `G4GPUEMSecondaryBuffer`,
   `G4GPUEMRngStream`, `G4GPUEMProcessSelector`, and `G4GPUEMStatusCode` before
   changing any deferred stub behavior.
2. Generate process-specific Geant4/tabulated validation fixtures and GPU-node
   evidence for photoelectric, pair-production, and bremsstrahlung.
3. Only after those gates pass may a later goal discuss detector/event workloads,
   benchmark result rows, physics-parity claims, speedup claims, or paper-ready
   EM transport evidence.
