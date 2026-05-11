# Phase 5d.3 cache-line aligned tracks — 2026-05-11 20:12 CEST

Lane: `g4gpu-phase5`
Subphase: `5d.3` (`include/g4gpu/Track.hh`)

## Summary

Added a cache-line-aligned fallback track representation: `alignas(64) g4gpu::Track`.
The layout is exactly one 64-byte cache line, and the alignment test verifies both
`alignof(Track) == 64` and vector allocation alignment. A packed legacy reference
layout remains available for A/B timing through `G4GPU_TRACK_DISABLE_ALIGNED=1`.

## Files

- `include/g4gpu/Track.hh`
- `src/core/Track.cc`
- `tests/test_track_alignment.cc`
- `benchmarks/events/BenchmarkDriver.hh`
- `benchmarks/profiles/phase5d3_track_alignment_20260511T2012.json`

## Focused verification

Build directory: `build_phase5d3`

```text
ctest --test-dir build_phase5d3 -R "g4gpu_cross_section_interpolator|g4gpu_branchless_solids|g4gpu_track_alignment|g4gpu_benchmark_manifest|g4gpu_benchmark_script_syntax|g4gpu_validate_harness|g4gpu_benchmark_.*_smoke" --output-on-failure
100% tests passed, 0 tests failed out of 12
```

Backend/layout probe:

```text
PASS: alignof(Track)=64, sizeof(Track)=64, backend=alignas64-track
```

## Packed vs aligned benchmark evidence

Each event used 10,000 generated events and seven repetitions. Timings are the
benchmark driver `total_wall_time_ns` field, covering row generation and the
aligned-track workload but not Parquet conversion.

| Event | Packed median ns | Aligned median ns | Speedup |
|---|---:|---:|---:|
| `gamma_100mev` | 173570977 | 168113852 | 1.032x |
| `muon_10gev` | 175287976 | 169139430 | 1.036x |
| `nbar_carbon` | 170514617 | 166180925 | 1.026x |
| `cosmic_shower` | 174605192 | 169339111 | 1.031x |
| `optical_scintillator` | 170084563 | 166629243 | 1.021x |
| `beam_neutron` | 170106374 | 166947070 | 1.019x |

All six event drivers show positive 5d.3 speedup. The full Phase 5
acceptance target of at least 1.8x on four events remains open for the
cumulative 5d stack.

## Validation evidence

For each event, 1,000-event packed-reference and aligned-track Parquet outputs
were compared with `benchmarks/validate.py`.

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

- 5d.1, 5d.2, and 5d.3 have positive speedup and validation evidence.
- 5d.4 navigation prefetch remains unstarted.
- A full GPU-node CTest should be run for this 5d.3 head before proceeding to
  5d.4, matching the lane pattern used for 5d.1 and 5d.2.
- Full Phase 5 DONE remains blocked until cumulative speedup/no-regression
  acceptance is satisfied.
