# EM/gamma validation fixture contract — 2026-05-12

## Scope

This contract defines the reference-data evidence required before any deferred
EM/gamma process can claim GPU validation. It is documentation/verifier coverage
only: no source kernel, physics table, secondary buffer, detector/event workload,
production output, physics-parity claim, or speedup claim is changed here.

Current baseline: `5b2a20a235b2491901d5480dccf5e2745c4cb930` has a validated
standalone Compton Klein-Nishina runtime gate plus fail-closed contracts,
contract index, and implementation roadmap for the deferred processes.

## Required fixture metadata

Every future photoelectric, pair-production, or bremsstrahlung validation
fixture must include:

1. **Reference provenance:** Geant4 version or tabulated-data source, physics
   list or data-library identifier, material definitions, production cuts, and a
   SHA-256 digest for every generated fixture file.
2. **Observable declaration:** exact observable names, units, binning or sample
   definition, and whether the comparison is a curve tolerance, conservation
   check, or distribution test.
3. **Statistics contract:** at least 10,000 samples for KS-style distribution
   checks where applicable and the repository standard `p > 0.05`; deterministic
   curve comparisons must specify absolute or relative tolerances before the GPU
   run is accepted.
4. **Process coverage:** photoelectric fixtures must cover attenuation and
   shell/energy accounting; pair-production fixtures must cover conversion
   probability, e-/e+ energy share, charge, and energy accounting;
   bremsstrahlung fixtures must cover radiative loss, emitted-photon spectrum,
   and post-step lepton-energy accounting.
5. **Failure mode:** missing fixture files, stale digests, incomplete material
   coverage, or missing `sacct`/CTest/GPU log evidence must keep the process
   fail-closed and must not be counted as validation.

## Current fail-closed evidence

- No `docs/fixtures/em_gamma/` validation dataset is present in this checkout.
- The existing GPU evidence is limited to the standalone 1 MeV Compton
  Klein-Nishina sampler and does not validate photoelectric, pair-production, or
  bremsstrahlung.
- The deferred-process contracts still require Geant4/tabulated references and
  process-specific GPU validation before any stub can become executable.

## Boundary

This contract does not authorize SLURM submission, table generation, detector or
event-driver execution, NNBAR production edits, optimized-result rows,
physics-parity claims, or speedup claims.
