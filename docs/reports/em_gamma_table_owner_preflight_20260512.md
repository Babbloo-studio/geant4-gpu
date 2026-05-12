# EM/gamma shared table-owner preflight contract — 2026-05-12

## Scope

This contract defines the fail-closed interface requirements for a future
`G4GPUEMPhysicsTables` owner. It is documentation/verifier coverage only: no
C++/CUDA table type is added, no `MaterialData` ABI field is changed, no kernel
runtime path is changed, and no photoelectric, pair-production, or
bremsstrahlung physics is implemented here.

Current baseline: `3da1592f71f04e0092b9b7147d8b8ddf82f6aac9` has Compton
Klein-Nishina validation, deferred-process contracts, an implementation roadmap,
and a validation-fixture contract. The roadmap names the shared EM table owner
as the first dependency before any deferred process can mutate tracks.

## Required future interface

A future `G4GPUEMPhysicsTables` implementation must be off-by-default and must
meet these requirements before `SamplePhotoelectric`, `SamplePair`, or
`SampleBremsstrahlung` leaves stub status:

1. **Separate owner / MaterialData ABI:** table storage is owned by `G4GPUEMPhysicsTables`, not by
   appending process-specific arrays to `MaterialData`; `MaterialData` remains
   the compact base material ABI with `Z_over_A`, `I`, `density`, `X0`, and
   `name` only.
2. **Device pointer bundle:** kernels receive an explicit nullable table-view or
   pointer bundle, with a labelled host-side preflight proving all required
   device pointers and grid dimensions are present before launch.
3. **Process families:** the owner has distinct metadata for photoelectric attenuation/shell accounting,
   pair-production conversion and energy-share tables, and bremsstrahlung radiative-loss/emitted-photon tables.
4. **Energy/material domain checks:** every lookup validates material index,
   energy range, bin monotonicity, and interpolation policy before returning a
   sampled process result.
5. **Missing-table gate:** missing, stale, or out-of-domain tables return a
   labelled fail-closed status code and do not mutate tracks, statuses, energies,
   directions, or any future secondary buffer.

## Acceptance evidence for a later implementation

The first code commit that introduces `G4GPUEMPhysicsTables` must include unit
coverage proving: default construction is disabled or empty, missing tables are
detected before a GPU launch, an explicit opt-in flag is required, table digest
or version metadata is checked, and no deferred-process stub mutates tracks when
its table family is absent.

## Boundary

This preflight does not authorize SLURM submission, table generation, detector
or event-driver execution, optimized-result rows, physics-parity claims, speedup claims, or use of NNBAR production code/data.
