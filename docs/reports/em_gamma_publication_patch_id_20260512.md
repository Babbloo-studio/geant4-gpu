# EM/gamma publication patch-id contract (2026-05-12)

## Scope

This report closes a publication-artifact gap: a current-head patch must not
only mention the live commit hash and subject, it must encode the same file
delta as the live `HEAD` commit.  This is a read-only fallback-publication gate
and does not authorize SLURM submission, detector/event execution, benchmark
production, speedup claims, or physics-parity claims.

## Contract

`g4gpu_em_publication_patch_id` verifies the current short `HEAD`, locates the
single fallback patch matching `patches/*-<head>.patch`, and compares stable
Git patch IDs:

- `git show --format=email --no-ext-diff HEAD | git patch-id --stable`
- `git patch-id --stable < patches/*-<head>.patch`

The two patch IDs must match exactly.  The verifier also requires the patch to
contain the current full commit hash and matching `[PATCH]` subject, preserving
the stronger metadata checks already performed by the current-head publication
artifact verifier.

## Boundary

The check is intentionally content-only and read-only.  It does not apply the
patch into any worktree, mutate publication artifacts, run benchmark binaries,
or promote the EM/gamma scaffold beyond its existing validated scope.
