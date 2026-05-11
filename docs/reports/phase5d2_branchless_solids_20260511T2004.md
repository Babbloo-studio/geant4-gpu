# Phase 5d.2 branchless solids optimization — 2026-05-11 20:04 CEST

Lane: `g4gpu-phase5`
Subphase: `5d.2` (`src/geometry/branchless_solids.cc`)

## Summary

Implemented Geant4-like `G4Box`/`G4Tubs` distance helpers for the CPU fallback path.
The box distance-to-in batch path uses branchless slab arithmetic with AVX2 runtime
dispatch when available; scalar branchless and explicit reference paths remain available
for portability and A/B checks. The reference path is selected with
`G4GPU_SOLIDS_DISABLE_BRANCHLESS=1`.

## Files

- `include/g4gpu/BranchlessSolids.hh`
- `src/geometry/branchless_solids.cc`
- `tests/test_branchless_solids.cc`
- `benchmarks/events/BenchmarkDriver.hh`
- `benchmarks/profiles/phase5d2_branchless_solids_20260511T2004.json`

## Focused verification

Build directory: `build_phase5d2`

```text
ctest --test-dir build_phase5d2 -R "g4gpu_cross_section_interpolator|g4gpu_branchless_solids|g4gpu_benchmark_manifest|g4gpu_benchmark_script_syntax|g4gpu_validate_harness|g4gpu_benchmark_.*_smoke" --output-on-failure
100% tests passed, 0 tests failed out of 11
```

Backend probe:

```text
PASS: branchless solids backend=avx2-box-branchless, samples=4096, max_abs=0
```

## Reference vs branchless benchmark evidence

Each event used 10,000 generated events and seven repetitions. Timings are the
benchmark driver `total_wall_time_ns` field, covering row generation and the
box surface-test workload but not Parquet conversion.

| Event | Reference median ns | Branchless median ns | Speedup |
|---|---:|---:|---:|
| `gamma_100mev` | 150688029 | 140283860 | 1.074x |
| `muon_10gev` | 150789549 | 140663704 | 1.072x |
| `nbar_carbon` | 151274150 | 140913645 | 1.074x |
| `cosmic_shower` | 151194085 | 141158215 | 1.071x |
| `optical_scintillator` | 151525178 | 140501089 | 1.078x |
| `beam_neutron` | 152160834 | 141284553 | 1.077x |

All six event drivers show positive 5d.2 speedup. This is an incremental L0
gain; the full Phase 5 acceptance target of at least 1.8x on four events
remains open for the cumulative 5d stack.

## Validation evidence

For each event, 1,000-event reference and branchless Parquet outputs were
compared with `benchmarks/validate.py` using the existing four observables.

| Event | Passed | Max KL | Min KS p-value |
|---|---:|---:|---:|
| `gamma_100mev` | true | 0 | 1 |
| `muon_10gev` | true | 0 | 1 |
| `nbar_carbon` | true | 0 | 1 |
| `cosmic_shower` | true | 0 | 1 |
| `optical_scintillator` | true | 0 | 1 |
| `beam_neutron` | true | 0 | 1 |

All validation comparisons passed.

## Remaining Phase 5 status

- 5d.1 and 5d.2 have positive speedup and validation evidence.
- 5d.3 cache-line aligned tracks and 5d.4 navigation prefetch remain unstarted.
- A full GPU-node CTest should be run for this 5d.2 head before proceeding to
  5d.3, matching the lane pattern used for 5d.1.
- Full Phase 5 DONE remains blocked until the cumulative speedup/no-regression
  acceptance gate is satisfied.
