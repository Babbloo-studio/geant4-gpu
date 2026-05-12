# EM/gamma secondary-buffer preflight contract — 2026-05-12

## Scope

This contract defines the fail-closed requirements for a future
`G4GPUEMSecondaryBuffer` used by deferred EM/gamma processes. It is
documentation/verifier coverage only: no secondary-buffer C++/CUDA type is
added, no `TrackSOA` field is changed, no kernel runtime path is changed, and
no pair-production or bremsstrahlung physics is implemented here.

Current baseline: `acc81cf2b57a5446c616577b6600978780cb6745` has a shared
EM table-owner preflight contract. The roadmap names an owned secondary buffer
as the second dependency, after table ownership and before process selection or
any process-specific implementation.

## Required future interface

A future `G4GPUEMSecondaryBuffer` implementation must be off-by-default and must
meet these requirements before `SamplePair` or `SampleBremsstrahlung` can leave
stub status:

1. **Separate owner / TrackSOA ABI:** secondary storage is owned by
   `G4GPUEMSecondaryBuffer`, not by appending process-specific arrays to
   `TrackSOA`; the current primary-track SoA remains unchanged until an explicit
   migration contract exists.
2. **Capacity contract:** the host preflight declares maximum secondary count,
   per-process emission limits, and a deterministic overflow policy before any
   GPU launch can write secondary records.
3. **Atomic reservation contract:** device writers reserve contiguous slots with
   a single labelled status path for success, overflow, and disabled-buffer
   cases; failed reservations must leave the primary track unmodified.
4. **Conservation contract:** every accepted secondary batch records enough
   parent id, particle code, energy, direction, time, material, and status
   metadata to check energy/charge conservation for pair production and
   bremsstrahlung before publication.
5. **Missing-buffer gate:** a null, disabled, undersized, or stale secondary
   buffer returns a labelled fail-closed status code and does not mutate primary tracks, energies, directions, statuses, table state, or output rows.

## Acceptance evidence for a later implementation

The first code commit that introduces `G4GPUEMSecondaryBuffer` must include unit
coverage proving: default construction is disabled or empty, missing buffers are
detected before launch, overflow is deterministic, accepted pair-production
batches create exactly one e-/e+ pair, accepted bremsstrahlung batches create one emitted gamma, rejected batches leave primary tracks unchanged, and all tests
remain isolated from detector/event workloads.

## Boundary

This preflight does not authorize SLURM submission, detector or event-driver
execution, output-row generation, table generation, physics-parity claims,
speedup claims, or use of NNBAR production code/data.
