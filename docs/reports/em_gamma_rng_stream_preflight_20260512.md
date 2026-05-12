# EM/gamma RNG-stream preflight contract — 2026-05-12

## Scope

This contract defines the fail-closed requirements for future EM/gamma random
number ownership before deferred processes become executable. It is
verification/planning coverage only: no RNG C++/CUDA type is added, no kernel
runtime path is changed, no physics table or secondary buffer is allocated, and
no photoelectric, pair-production, or bremsstrahlung physics is implemented.

Current baseline: the EM interface accepts one `curandState*` per track or
sample, and `tests/test_em_klein_nishina.cu` initializes a fixed seed for the
standalone Compton sampler. That is enough for the current single-process
Klein-Nishina gate, but it is not enough to promote multiple competing EM
processes because future process selection and secondary emission will consume
variable numbers of uniforms.

## Required future interface

A future `G4GPUEMRngStream` implementation must be off-by-default and must meet
these requirements before `SamplePhotoelectric`, `SamplePair`, or
`SampleBremsstrahlung` can leave stub status:

1. **Owner contract:** EM/gamma kernels receive a labelled RNG stream object or
   descriptor rather than silently sharing an unversioned `curandState*` across
   process-selection, table sampling, and secondary-buffer writes.
2. **Seed provenance contract:** host preflight records seed, subsequence,
   offset policy, RNG engine, number of states, and the mapping from track index
   to stream before any GPU launch can mutate primary tracks or secondary
   buffers.
3. **Consumption contract:** every process-specific sampler declares the maximum
   random draws used by its accept/reject loop or table lookup, plus a bounded
   retry/overflow policy for rare tails.
4. **Replay contract:** validation fixtures can rerun the same event/sample with
   identical seed provenance and reproduce either bit-identical fallback output
   or a documented statistical-equivalence mode.
5. **Missing-RNG gate:** a null, undersized, stale, or disabled RNG stream
   returns a labelled fail-closed status and does not mutate primary tracks,
   secondary buffers, physics tables, result rows, or publication artifacts.

## Acceptance evidence for a later implementation

The first code commit that introduces `G4GPUEMRngStream` must include unit
coverage proving: missing/undersized streams fail before launch, seed metadata is
serialized in a host-side preflight artifact, Compton validation still passes
with the existing fixed-seed path, process-specific bounded retry counters are
observable, and pair-production or bremsstrahlung secondary emission can be
replayed with the same seed tuple.

## Boundary

This preflight does not authorize SLURM submission, detector or event-driver
execution, output-row generation, reference regeneration, physics-parity claims,
speedup claims, or use of NNBAR production code/data.
