# EM/gamma status-code preflight contract — 2026-05-12

## Scope

This contract defines the fail-closed requirements for future EM/gamma status
codes shared by table ownership, RNG streams, secondary buffers, process
selection, and per-process samplers. It is documentation/verifier coverage only:
no status enum is added, no `EMInteractionResult` ABI is changed, no kernel
runtime path is changed, and no photoelectric, pair-production, or
bremsstrahlung physics is implemented.

Current baseline: `EMInteractionResult` carries a plain integer `status`, the
Compton scaffold treats `status == 0` as success, and deferred stubs return an
empty result. That is sufficient for the current single-process test scaffold,
but future fail-closed paths need a named status vocabulary before they can be
used for process selection, secondary-buffer overflow, table-missing, or
RNG-missing cases.

## Required future interface

A future `G4GPUEMStatusCode` implementation must be off-by-default and must
meet these requirements before deferred processes can report anything other than
stub/no-op status:

1. **Named status vocabulary:** define stable names for success, disabled
   process, missing table, missing RNG, missing secondary buffer, table-domain
   miss, secondary overflow, unsupported particle, and validation-only slow path.
2. **No silent mutation contract:** every non-success status leaves primary
   tracks, secondary buffers, physics tables, RNG state, result rows, and
   publication artifacts unchanged unless a later contract explicitly names a
   recoverable slow path.
3. **Host visibility contract:** launch wrappers or validation collectors expose
   enough status counters for tests to assert which fail-closed path occurred;
   kernel-only integer codes are insufficient for publication evidence.
4. **Compatibility contract:** the existing Compton success path remains
   `status == 0` until an explicit ABI migration updates `EMInteractionResult`,
   the static contract, and the Klein-Nishina validation test together.
5. **Documentation contract:** every per-process verifier that permits a new
   status must cite the corresponding status-code name and prove that unsupported
   cases do not fall through to another physics process.

## Acceptance evidence for a later implementation

The first code commit that introduces `G4GPUEMStatusCode` must include unit
coverage proving: each named non-success status can be produced by a fixture,
status counters are visible on the host, success status preserves the current
Compton validation path, unsupported particle and missing-resource cases do not
mutate tracks, and CTest/verifier coverage fails if a sampler introduces a raw
unnamed nonzero status.

## Boundary

This preflight does not authorize SLURM submission, detector or event-driver
execution, output-row generation, reference regeneration, physics-parity claims,
speedup claims, ABI migration, or use of NNBAR production code/data.
