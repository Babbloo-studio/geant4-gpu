# EM/gamma pair-production contract gate — 2026-05-12

## Scope

This gap-scan artifact defines the minimum contract that must exist before the
`TODO Phase 2.EM-pair` stub can become executable GPU physics. It is a
fail-closed design gate only: no source kernel, physics table, secondary buffer,
detector/event workload, production output, parity claim, or speedup claim is
changed here.

Current baseline: `c4cf3fcc954b11230ad45a505421a4485cae7a00` has a GPU-passed
Compton Klein-Nishina runtime gate and a photoelectric contract gate, but pair
production remains a no-op stub in `src/physics/EMStepKernel.cu`.

## Required implementation contract

1. **Physics-table schema:** add an explicit `G4GPUPairProductionTable`-style
   owner with per-material monotonic photon-energy grids above the `2*m_e`
   threshold, total pair-conversion attenuation coefficients, nuclear-field and
   electron-field components, screening parameters, and cumulative sampling
   tables for the positron energy fraction. `MaterialData` alone is
   insufficient because it only stores `Z_over_A`, `I`, `density`, `X0`, and
   `name`.
2. **Process-selection gate:** `EMStep` must select pair production only when a
   valid table covers the track material and gamma energy above threshold;
   missing tables or sub-threshold gammas must take a labelled slow/fail-closed
   path rather than faking a conversion.
3. **Primary/secondary convention:** a real conversion must set
   `EMInteractionResult.process = kPairProduction`, kill or mark the primary
   gamma with a documented `TrackSOA.status` value, and enqueue exactly one
   electron plus one positron in an owned EM secondary buffer.
4. **Kinematic policy:** the implementation must conserve energy event by event
   (`E_gamma = E_e- + E_e+ + 2*m_e` in kinetic-energy bookkeeping), define the
   angular approximation used for the two secondaries, and label any local
   recoil/atomic-screening approximation. Silent momentum or charge loss is
   forbidden.
5. **Validation gate:** before DONE, compare total attenuation or mean-free-path
   curves against Geant4 or tabulated references for at least three materials,
   validate the sampled positron energy-fraction distribution where a reference
   is available, and run energy/charge-accounting closure over at least 10,000
   samples. Distribution checks must use the repository statistical standard
   (`p > 0.05` where a KS test is applicable).

## Current fail-closed evidence

- `SamplePair` still contains `TODO Phase 2.EM-pair` and clears its result
  (`out = {};`) before returning.
- `scripts/verify_em_gamma_stub_fail_closed.py` keeps the pair-production stub
  non-mutating until a separate implementation updates the contract and tests.
- `scripts/verify_em_gamma_deferred_process_gap.py` still lists missing
  physics-table, secondary-buffer, process-selection, and validation contracts.
- No `G4GPUPairProductionTable` or EM secondary buffer exists in the current
  public interface.

## Follow-up sequence

1. Add the pair-production table, secondary-buffer, and status interfaces with
   tests that fail closed on missing data.
2. Add a Geant4/tabulated reference generator or fixture for pair attenuation
   and energy-fraction curves.
3. Implement pair conversion behind the table-validity and threshold gates only.
4. Run a dedicated GPU-node pair-production validation and archive job-specific
   evidence, separate from the Compton runtime gate.
