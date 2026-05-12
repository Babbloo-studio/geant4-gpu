# Benchmark generated-artifact ignore guard — 2026-05-12

## Scope

The Phase 5 harness now generates large or machine-local artifacts during
reference generation and measurement runs. Those artifacts are evidence inputs,
but they should not become accidental source changes in `lane/g4gpu-phase5`.

## Guard

The reusable verifier `scripts/verify_benchmark_generated_artifact_ignores.py`
requires `.gitignore` coverage and CTest registration for generated harness
outputs:

- `benchmarks/reference/` reference Parquet trees and `MANIFEST.sha256`
- `benchmarks/raw/` per-seed stdout/stderr captures
- `benchmarks/hardware_evidence/` SLURM and node fingerprints
- `benchmarks/build_logs/` configure/build transcripts
- `benchmarks/results/results.parquet` append-only result table

The guard also fails if any file under the generated `reference`, `raw`,
`hardware_evidence`, `build_logs`, or `results` trees is tracked by git.
Publication bundles, checksum manifests, compact reports, and curated perf
profile artifacts remain separate and may still be committed intentionally.

## Verification

CTest target: `g4gpu_benchmark_generated_artifact_ignores`.

Expected direct verifier marker: `BENCHMARK_GENERATED_ARTIFACT_IGNORES_OK`.

No SLURM submission, event/reference run, result-row write, parity/speedup
promotion, optimized install-prefix claim, or NNBAR production edit is part of
this guard.
