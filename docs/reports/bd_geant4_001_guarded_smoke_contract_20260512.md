# BD-geant4-001 guarded-smoke contract preflight

Date: 2026-05-12
Lane: `g4gpu-phase5`
Scope: read-only preflight only; no SLURM submission, no event execution, no
reference generation, no result-row append, no parity/speedup promotion, and no
NNBAR production edit.

## Contract added

Commit candidate adds `benchmarks/harness/bd001_smoke_contract.py`, a
fail-closed guard for the first future BD-geant4-001 smoke/result-row attempt.
The guard composes the reviewed-registry gate and then requires a contract that
names all of the following before any smoke work is allowed:

- `source_ref` exactly matching the reviewed branch and commit as
  `<branch>@<40-hex-sha>`.
- an absolute `reference_dataset` directory with `MANIFEST.sha256` and existing
  Parquet manifest entries, with optional workload and physics-list coverage
  checks.
- a non-promotional `result_tag` (`SPEEDUP` is rejected for guarded smoke).
- a non-paper `claim_level` (`L3`/`L4` are rejected).
- explicit no-promotion checks: `result_tag_not_speedup`,
  `claim_level_not_paper`, `manual_promotion_required`, and
  `dry_run_no_results_append`.

## Verification intent

The focused test creates a local fixture Geant4 source repo, approved registry
row, review artifact, reference manifest, and guarded-smoke contract. It verifies
acceptance for the complete fixture and fail-closed behavior for mismatched
source refs, incomplete reference coverage, `SPEEDUP` result tags, and missing
no-promotion checks.

This is still prerequisite coverage only. It does not create a real BD-001
implementation branch, production registry row, reference dataset, SLURM smoke,
measurement row, parity result, or speedup claim.
