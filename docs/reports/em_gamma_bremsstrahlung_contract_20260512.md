# EM/gamma bremsstrahlung contract gate — 2026-05-12

## Scope

This gap-scan artifact defines the minimum contract that must exist before the
`TODO Phase 2.EM-bremsstrahlung` stub can become executable GPU physics. It is a
fail-closed design gate only: no source kernel, physics table, secondary buffer,
detector/event workload, production output, parity claim, or speedup claim is
changed here.

Current baseline: `c8462cbefde89d45b4d5a3dc77a3bbe23765c285` has a GPU-passed
Compton Klein-Nishina runtime gate plus photoelectric and pair-production
contract gates, but electron/positron bremsstrahlung remains a no-op stub in
`src/physics/EMStepKernel.cu`.

## Required implementation contract

1. **Physics-table schema:** add an explicit `G4GPUBremsstrahlungTable`-style
   owner with per-material monotonic lepton-energy grids, total radiative-loss
   rates, differential photon-energy cumulative distribution functions,
   electron/positron model labels, and low-energy cuts. `MaterialData` alone is
   insufficient because it only stores `Z_over_A`, `I`, `density`, `X0`, and
   `name`.
2. **Process-selection gate:** `EMStep` must select bremsstrahlung only when a
   valid table covers the lepton material, particle charge, kinetic energy, and
   configured photon-production cut; missing tables must take a labelled
   slow/fail-closed path rather than emitting a fake photon.
3. **Primary/secondary convention:** a real emission must set
   `EMInteractionResult.process = kBremsstrahlung`, reduce the primary lepton
   kinetic energy by the sampled photon kinetic energy, keep charge and PDG
   identity unchanged, and enqueue exactly one gamma in an owned EM secondary
   buffer.
4. **Kinematic policy:** the implementation must define the angular model for
   the emitted photon and recoil lepton, conserve kinetic energy event by event,
   and label any condensed-history approximation. Silent photon dropping or
   negative lepton energy is forbidden.
5. **Validation gate:** before DONE, compare stopping-power or radiative-loss
   curves and emitted-photon spectra against Geant4 or tabulated references for
   at least three materials and both e-/e+ where applicable. Distribution checks
   must use the repository statistical standard (`p > 0.05`) with at least
   10,000 samples where a KS test is applicable, plus energy/charge-accounting
   closure for every sampled event.

## Current fail-closed evidence

- `SampleBremsstrahlung` still contains `TODO Phase 2.EM-bremsstrahlung` and
  clears its result (`out = {};`) before returning.
- `scripts/verify_em_gamma_stub_fail_closed.py` keeps the bremsstrahlung stub
  non-mutating until a separate implementation updates the contract and tests.
- `scripts/verify_em_gamma_deferred_process_gap.py` still lists missing
  physics-table, secondary-buffer, process-selection, and validation contracts.
- No `G4GPUBremsstrahlungTable` or EM secondary buffer exists in the current
  public interface.

## Follow-up sequence

1. Add the bremsstrahlung table, secondary-buffer, production-cut, and status
   interfaces with tests that fail closed on missing data.
2. Add a Geant4/tabulated reference generator or fixture for radiative loss and
   emitted-photon spectra.
3. Implement bremsstrahlung behind the table-validity and cut gates only.
4. Run a dedicated GPU-node bremsstrahlung validation and archive job-specific
   evidence, separate from the Compton runtime gate.
