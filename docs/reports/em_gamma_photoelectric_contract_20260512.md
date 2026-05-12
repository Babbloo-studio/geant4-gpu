# EM/gamma photoelectric contract gate — 2026-05-12

## Scope

This gap-scan artifact defines the minimum contract that must exist before the
`TODO Phase 2.EM-photoelectric` stub can become executable GPU physics. It is a
fail-closed design gate only: no source kernel, physics table, track status,
secondary emission, detector/event workload, production output, parity claim, or
speedup claim is changed here.

Current baseline: `de22fb0daa1565a3f31a35530fde06fff5191964` has a GPU-passed
Compton Klein-Nishina runtime gate, but photoelectric absorption remains a no-op
stub in `src/physics/EMStepKernel.cu`.

## Required implementation contract

1. **Physics-table schema:** add an explicit `G4GPUEMPhysicsTable`-style owner
   with per-material monotonic energy grids, total photoelectric attenuation
   coefficients, per-shell cross sections, shell binding energies, and cumulative
   shell-selection probabilities. `MaterialData` alone is insufficient because it
   only stores `Z_over_A`, `I`, `density`, `X0`, and `name`.
2. **Process-selection gate:** `EMStep` must select photoelectric absorption only
   when a valid table covers the track material and gamma energy; missing tables
   must take a labelled slow/fail-closed path rather than falling through to a
   fake interaction.
3. **Track-status convention:** a real absorption must set
   `EMInteractionResult.process = kPhotoelectric`, set `kill_primary = true`,
   deposit or account for the absorbed primary energy, and use a documented
   `TrackSOA.status` value for killed primary gammas.
4. **Secondary policy:** fluorescence and Auger emission must either be disabled
   by an explicit local-deposition mode or routed through an owned EM secondary
   buffer. Silent secondary dropping is forbidden.
5. **Validation gate:** before DONE, compare attenuation/mean-free-path curves
   against Geant4 or tabulated references for at least three representative
   materials and run shell-selection/energy-accounting closure when secondaries
   are enabled. Distribution checks must use the repository statistical standard
   (`p > 0.05`, at least 10,000 samples where a KS test is applicable).

## Current fail-closed evidence

- `SamplePhotoelectric` still contains `TODO Phase 2.EM-photoelectric` and clears
  its result (`out = {};`) before returning.
- `scripts/verify_em_gamma_stub_fail_closed.py` keeps the photoelectric stub
  non-mutating until a separate implementation updates the contract and tests.
- `scripts/verify_em_gamma_deferred_process_gap.py` still lists missing
  physics-table, secondary-buffer, process-selection, and validation contracts.
- No `G4GPUEMPhysicsTable` or EM secondary buffer exists in the current public
  interface.

## Follow-up sequence

1. Add the table/secondary/status interfaces with tests that fail closed on
   missing data.
2. Add a Geant4/tabulated reference generator or fixture for material attenuation
   curves.
3. Implement photoelectric absorption behind the table-validity gate only.
4. Run a dedicated GPU-node photoelectric validation and archive job-specific
   evidence, separate from the Compton runtime gate.
