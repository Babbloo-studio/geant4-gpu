# EM/gamma deferred-process contract index — 2026-05-12

## Scope

This index ties the three deferred EM/gamma process stubs to their explicit
fail-closed implementation contracts. It does not implement photoelectric,
pair-production, or bremsstrahlung physics, does not change any kernel runtime
path, and does not claim detector/event validation, physics parity, or speedup.

Current baseline: `7c1b9c9c8205105d51648527d34c6f9473c2781b` keeps Compton as
the only executable EM/gamma process and leaves the three non-Compton processes
as documented no-op stubs in `src/physics/EMStepKernel.cu`.

## Contract coverage matrix

| Deferred process | Stub marker | Contract artifact | CTest gate | Remaining fail-closed blocker |
|------------------|-------------|-------------------|------------|--------------------------------|
| Photoelectric absorption | `TODO Phase 2.EM-photoelectric` | `docs/reports/em_gamma_photoelectric_contract_20260512.md` | `g4gpu_em_photoelectric_contract` | No `G4GPUEMPhysicsTable`, no shell/fluorescence/Auger secondary policy implementation, and no attenuation validation run |
| Pair production | `TODO Phase 2.EM-pair` | `docs/reports/em_gamma_pair_contract_20260512.md` | `g4gpu_em_pair_contract` | No `G4GPUPairProductionTable`, no owned EM secondary buffer for e-/e+, and no pair-conversion validation run |
| Bremsstrahlung | `TODO Phase 2.EM-bremsstrahlung` | `docs/reports/em_gamma_bremsstrahlung_contract_20260512.md` | `g4gpu_em_bremsstrahlung_contract` | No `G4GPUBremsstrahlungTable`, no owned EM secondary buffer for emitted gammas, and no radiative-loss validation run |

## Shared invariants

- `scripts/verify_em_gamma_stub_fail_closed.py` must continue to prove all three
  deferred stubs clear `out = {};` and return without mutating process outputs.
- `scripts/verify_em_gamma_deferred_process_gap.py` must continue to prove the
  scaffold has no secondary queue and that `TrackSOA` lacks secondary ownership.
- `scripts/verify_em_gamma_static_contract.py` must require all three
  per-process contract CTest targets plus this index verifier.
- A future executable implementation must update the relevant contract report,
  replace the stub-fail-closed expectation with new table/secondary/status tests,
  and archive a process-specific GPU validation run.

## Boundary

The archived GPU evidence remains limited to the standalone 1 MeV Compton
Klein-Nishina sampler. This index is documentation and verifier coverage only;
it is not a detector/event run, NNBAR production edit, optimized-result row,
physics-parity claim, or speedup claim.
