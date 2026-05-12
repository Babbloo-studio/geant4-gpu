# EM/gamma deferred implementation roadmap — 2026-05-12

## Scope

This roadmap sequences the shared work required before the deferred EM/gamma
stubs can become executable GPU physics. It is a planning artifact only: it does
not implement photoelectric, pair-production, or bremsstrahlung physics, does not
change any kernel runtime path, and does not claim detector/event validation,
physics parity, or speedup.

Current baseline: `fb0798cc38fbc1be7b4b20284c439a7fe7587aea` has one validated
standalone Compton Klein-Nishina runtime gate and fail-closed contracts for the
three deferred processes.

## Dependency order

1. **Shared EM table owner:** define an off-by-default `G4GPUEMPhysicsTables`
   interface that can own the photoelectric, pair-production, and
   bremsstrahlung tables without changing the current `MaterialData` ABI.
   Acceptance evidence: unit tests prove missing tables are detected and do not
   mutate tracks.
2. **Owned secondary buffer:** add an EM secondary-buffer interface for emitted
   gammas and charged pairs before pair production or bremsstrahlung can leave
   stub status. Acceptance evidence: capacity, overflow, and conservation tests
   fail closed before kernel mutation.
3. **Process-selection contract:** replace the current gamma-always-Compton
   placeholder with an explicit material/energy process selector only after the
   table owner exists. Acceptance evidence: missing-table and out-of-range cases
   take labelled slow/fail-closed paths.
4. **Per-process implementations:** implement photoelectric first (one killed
   primary plus optional local deposition), then pair production (two charged
   secondaries), then bremsstrahlung (one emitted gamma plus lepton recoil).
   Acceptance evidence: each process updates its contract report and verifier in
   the same commit that changes the stub expectation.
5. **GPU validation and publication:** run a dedicated GPU-node validation per
   process using Geant4/tabulated references, then refresh the publication
   bundle/checksum/current-verifier chain. Acceptance evidence: archived logs,
   `sacct`, CTest output, and strict verifier `OK` markers for each process.

## Cross-cutting invariants

- `SampleCompton` remains the only executable process until the shared table and
  secondary-buffer interfaces are present and tested.
- `SamplePhotoelectric`, `SamplePair`, and `SampleBremsstrahlung` remain
  fail-closed stubs until their process-specific validation evidence exists.
- No NNBAR source, library, macro, production output, or reconstruction package
  is used to close any G4GPU-only gate.
- No optimized-result row, detector/event validation, physics-parity claim, or
  speedup claim is made by this roadmap.

## Roadmap verifier

`scripts/verify_em_gamma_implementation_roadmap.py` checks this dependency order
against the current contract index, per-process contract reports, stub verifier,
and CMake registration. A future implementation that changes the dependency
order must update this roadmap and verifier together.
