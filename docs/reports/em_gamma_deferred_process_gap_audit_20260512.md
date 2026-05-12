# EM/gamma deferred-process gap audit

Date: 2026-05-12
Checkout: `/projects/hep/fs10/shared/nnbar/billy/geant4-gpu-em-gamma`
Branch: `lane/g4gpu-em-gamma`

## Purpose

The current EM/gamma compact unit intentionally implements only the
Klein-Nishina Compton path. This audit records why the other advertised
electron/positron/gamma processes must remain fail-closed stubs until the
interface has enough physics-table, secondary-buffer, and validation coverage.

## Current artifact boundary

- `include/g4gpu/EMStepKernel.hh` declares `SamplePhotoelectric`,
  `SampleCompton`, `SamplePair`, `SampleBremsstrahlung`, `EMStep`, and launch
  wrappers.
- `src/physics/EMStepKernel.cu` routes live gamma tracks through
  `SampleCompton` and leaves the other three process functions as explicit
  `TODO Phase 2.EM-*` no-ops.
- `tests/test_em_klein_nishina.cu` validates only the single-scatter Compton
  scattered-photon energy distribution.
- `scripts/verify_em_gamma_runtime_gate.py` requires a future GPU-node KS PASS
  before runtime validation can be claimed.

## Deferred-process blockers

| Process | Current stub marker | Minimum missing contract before implementation | Required validation before DONE |
|---------|---------------------|-----------------------------------------------|---------------------------------|
| Photoelectric absorption | `TODO Phase 2.EM-photoelectric` | Per-material shell cross-section tables, shell binding energies, fluorescence/Auger secondary policy, and an absorption/track-kill status convention | Energy-dependent absorption mean free path against Geant4 or tabulated reference, plus secondary-energy closure when fluorescence/Auger is enabled |
| Pair production | `TODO Phase 2.EM-pair` | Nuclear/electron-field pair cross sections, threshold handling, positron/electron energy and angle sampler, and a GPU secondary buffer capable of emitting two charged tracks | Conversion probability and e-/e+ energy-share KS tests against Geant4 above threshold |
| Bremsstrahlung | `TODO Phase 2.EM-bremsstrahlung` | Charged-lepton differential photon-emission tables, step-limiting mean-free-path sampling, recoil bookkeeping, and a GPU secondary buffer for emitted photons | Photon-energy spectrum and post-step lepton-energy KS tests against Geant4 for e-/e+ in representative materials |

## Shared interface gaps

1. **Physics-table schema:** `MaterialData` currently provides only compact
   material scalars (`Z_over_A`, `I`, `density`, `X0`, name). It is not a
   cross-section table or shell/energy-grid container.
2. **Secondary emission:** `TrackSOA` holds one active track collection and does
   not expose an owned secondary queue. Pair production and bremsstrahlung must
   not be implemented by silently dropping secondaries.
3. **Process selection:** `EMStep` currently chooses Compton for all live gamma
   tracks. A later implementation needs energy/material-dependent process
   competition and explicit slow-path labels when a process lacks a valid table.
4. **Validation scope:** `docs/VALIDATION.md` defines KS p-value `> 0.05` and
   at least 10,000 events for distribution comparisons; only the Compton
   single-scatter scaffold currently has a concrete test.

## Follow-up gates

- Add an explicit `G4GPUPhysicsTable` or equivalent EM-table contract before any
  non-Compton process can leave stub status.
- Add a secondary-buffer contract and accounting test before pair production or
  bremsstrahlung emits tracks.
- Add per-process GPU tests and keep no-device execution separate from physics
  PASS evidence via the runtime gate.
- Keep NNBAR production isolated: no NNBAR source, library, production macro, or
  output should be used to close this G4GPU-only process gap.

## Audit verifier

`scripts/verify_em_gamma_deferred_process_gap.py` checks this report against the
source-level stub markers and current interface constraints. A future
implementation that removes a stub must update the report and verifier in the
same commit, then provide the new validation evidence.

The verifier is also registered as CTest target
`g4gpu_em_deferred_process_gap` when CMake can find a Python 3 interpreter.
