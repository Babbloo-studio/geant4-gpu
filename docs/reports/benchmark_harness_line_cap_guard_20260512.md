# Benchmark harness line-cap guard — 2026-05-12

This report records a compact guard for the Phase 5 benchmark harness after the
BD001 reviewed-registry handoff briefly pushed `benchmarks/harness/run.py` and
`benchmarks/harness/tests/test_run.py` above the 500-line file cap.

Corrective commit `7f13adf` split helper logic into
`benchmarks/harness/run_helpers.py` and moved BD001 registry/run tests into
`benchmarks/harness/tests/test_run_bd001_registry.py` while preserving the
fail-closed `BD001_REVIEW_REGISTRY_HANDOFF_BLOCKED_782D84C_OK` behavior.

The reusable verifier `scripts/verify_benchmark_harness_line_caps.py` scans all
text-like files under `benchmarks/harness/` plus the compact benchmark/BD001
guard surfaces (`CMakeLists.txt`, `scripts/verify_bd001_smoke_readiness.py`,
`scripts/verify_benchmark*.py`,
`docs/reports/bd_geant4_001_smoke_readiness_20260512.md`,
`docs/reports/bd_geant4_001*.md`, and `docs/reports/benchmark_*guard*.md`). It
fails if any watched file exceeds 500 lines and self-checks this report plus
CMake registration as CTest target `g4gpu_benchmark_harness_line_caps`.

Boundary: this is static hygiene only. It does not submit SLURM, run events,
regenerate references, append result rows, claim parity/speedup, approve BD001,
or edit NNBAR production code/data.
