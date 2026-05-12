# EM/gamma process-selector preflight contract — 2026-05-12

## Scope

This contract defines the fail-closed requirements for the future EM/gamma
process selector that will replace the current gamma-always-Compton placeholder.
It is verification/planning coverage only: no process-selector C++/CUDA type is
added, no kernel runtime path is changed, no physics table or secondary buffer
is allocated, and no photoelectric, pair-production, or bremsstrahlung physics
is implemented.

Current baseline: `EMStep` dispatches gamma tracks directly to `SampleCompton`,
while electron and positron tracks call the still-stubbed bremsstrahlung path.
That is correct for the current Klein-Nishina scaffold, but it must remain
blocked before publication-level EM transport because material/energy-dependent
competition between photoelectric absorption, Compton scattering, pair
production, and bremsstrahlung is not represented.

## Required future interface

A future `G4GPUEMProcessSelector` implementation must be off-by-default and
must meet these requirements before any deferred process can leave stub status:

1. **Table-backed process competition:** gamma selection uses explicit
   photoelectric, Compton, and pair-production macroscopic cross-section tables;
   lepton selection uses explicit bremsstrahlung tables and preserves any future
   continuous-loss boundary.
2. **Energy/material domain gate:** every selected table lookup validates
   material index, particle type, kinetic-energy range, and threshold behavior
   before a sampler can mutate primary tracks or reserve secondary-buffer slots.
3. **RNG draw contract:** process competition consumes a labelled RNG draw from
   the EM RNG stream and records enough provenance to replay the same selected
   process for validation fixtures.
4. **Fallback/slow-path contract:** missing tables, out-of-range energies, null
   RNG streams, disabled secondary buffers, or unsupported particles take a
   labelled fail-closed or explicitly slow CPU-validation path; they must not
   silently fall back to Compton.
5. **Histogram validation contract:** validation artifacts include selected
   process histograms versus Geant4/tabulated expectations for each particle,
   material, and energy grid before any speedup or parity claim is made.

## Acceptance evidence for a later implementation

The first code commit that introduces `G4GPUEMProcessSelector` must include unit
coverage proving: missing tables and out-of-range energies fail before kernel
mutation, thresholds choose no forbidden process, pair production is impossible
below threshold, process histograms match tabulated branch probabilities within
a declared statistical tolerance, and the current Compton-only validation path
continues to pass.

## Boundary

This preflight does not authorize SLURM submission, detector or event-driver
execution, output-row generation, reference regeneration, physics-parity claims,
speedup claims, or use of NNBAR production code/data.
