# EM/gamma publication-artifacts audit — 2026-05-12

## Scope

This audit locks the fallback-publication artifact gate for the EM/gamma lane.
It is a verifier/documentation artifact only: no kernel runtime path, physics
table, secondary buffer, detector/event workload, benchmark result row, SLURM
job, or production output is changed here.

## Required artifact set

For the live `lane/g4gpu-em-gamma` head, the publication directory must contain
exactly one current-head instance of each artifact class:

- `lane-g4gpu-em-gamma-<head>.bundle` with a successful `git bundle verify`
  transcript in `BUNDLE_VERIFY_<head>.txt`, and `git bundle list-heads` must
  include the exact current commit hash.
- `MIRROR_VERIFY_<head>.txt` proving the fork ref
  `refs/heads/lane/g4gpu-em-gamma` and local `HEAD` both resolve to the exact
  current commit hash.
- One patch under `patches/*-<head>.patch` whose `From` header contains the
  exact current commit hash and whose subject matches the current commit
  subject.
- `check_em_gamma_current_<head>.sh` and its latest transcript ending in the
  matching `EM_GAMMA_CURRENT_<HEAD>_OK` marker.
- One `SHA256SUMS-<head>-*` manifest that covers the bundle, patch, bundle
  verification transcript, mirror verification transcript, current verifier
  script, and latest transcript.

The gate is intentionally head-sensitive. A later commit must not keep passing
against older fallback artifacts; it must publish a fresh current-head bundle,
patch, verifier transcript, and checksum manifest before the CTest target is
green again.

## Boundary

Passing `g4gpu_em_publication_artifacts` only proves that fallback publication
artifacts for the current EM/gamma head exist, list the current commit in the
bundle heads, prove the fork mirror points at the same current commit, carry a
matching current-head patch, and match their manifest. It does not authorize
SLURM submission, detector or event-driver execution, output-row generation,
reference regeneration, physics-parity claims, speedup claims, ABI migration,
or executable photoelectric, pair-production, or bremsstrahlung implementation.
