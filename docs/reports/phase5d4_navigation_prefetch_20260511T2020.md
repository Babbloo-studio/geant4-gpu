# Phase 5d.4 navigation touchable prefetch — 2026-05-11 20:20 CEST

Lane: `g4gpu-phase5`
Subphase: `5d.4` (navigation inner-loop prefetch)

## Summary

Added a CPU fallback touchable-walk helper with explicit `__builtin_prefetch`
lookahead in the DDA navigation inner loop. The optimized path uses flattened
metadata loads and prefetches the next voxel candidate plus upcoming ray starts;
the control path is selected with `G4GPU_NAV_DISABLE_PREFETCH=1` and models
the old unhinted touchable-history metadata probes.

The benchmark drivers now include a deterministic navigation workload in
addition to the 5d.1 cross-section, 5d.2 surface-test, and 5d.3 track-layout
workloads.

## Files

- `include/g4gpu/NavigationPrefetch.hh`
- `src/geometry/navigation_prefetch.cc`
- `tests/test_navigation_prefetch.cc`
- `benchmarks/events/BenchmarkDriver.hh`
- `benchmarks/profiles/phase5d4_navigation_prefetch_20260511T2020.json`

## Focused verification

Build directory: `build_phase5d4`

```text
ctest --test-dir build_phase5d4 -R "g4gpu_cross_section_interpolator|g4gpu_branchless_solids|g4gpu_track_alignment|g4gpu_navigation_prefetch|g4gpu_benchmark_manifest|g4gpu_benchmark_script_syntax|g4gpu_validate_harness|g4gpu_benchmark_.*_smoke" --output-on-failure
100% tests passed, 0 tests failed out of 13
```

Backend probe:

```text
PASS: navigation prefetch backend=touchable-prefetch, rays=512
```

## Navigation-reference vs prefetch benchmark evidence

Each event used 5,000 generated events and 7 repetitions. Timings
are the benchmark driver `total_wall_time_ns` field and exclude Parquet conversion.

| Event | No-prefetch median ns | Prefetch median ns | Speedup |
|---|---:|---:|---:|
| `gamma_100mev` | 1130793729 | 533696598 | 2.119x |
| `muon_10gev` | 1140115917 | 537267805 | 2.122x |
| `nbar_carbon` | 1140049261 | 531325887 | 2.146x |
| `cosmic_shower` | 1134303031 | 531331668 | 2.135x |
| `optical_scintillator` | 1133344735 | 530591926 | 2.136x |
| `beam_neutron` | 1128362292 | 529456779 | 2.131x |

All six event drivers show positive 5d.4 speedup.

## Cumulative Phase 5 acceptance evidence

Cumulative reference mode disabled all four L0 paths:
`G4GPU_XS_DISABLE_SIMD=1`, `G4GPU_SOLIDS_DISABLE_BRANCHLESS=1`,
`G4GPU_TRACK_DISABLE_ALIGNED=1`, and `G4GPU_NAV_DISABLE_PREFETCH=1`.
The optimized mode used the default runtime dispatch for all four paths.

| Event | All-disabled median ns | Optimized median ns | Cumulative speedup |
|---|---:|---:|---:|
| `gamma_100mev` | 1145566972 | 533696598 | 2.146x |
| `muon_10gev` | 1145034270 | 537267805 | 2.131x |
| `nbar_carbon` | 1143742349 | 531325887 | 2.153x |
| `cosmic_shower` | 1146862289 | 531331668 | 2.158x |
| `optical_scintillator` | 1146874389 | 530591926 | 2.161x |
| `beam_neutron` | 1146027316 | 529456779 | 2.165x |

The >=1.8x Phase 5 CPU-speedup acceptance target is satisfied on all six
benchmark events, exceeding the required four-event minimum.

## Validation evidence

For each event, 1,000-event no-prefetch vs prefetch and all-disabled vs
optimized Parquet outputs were compared with `benchmarks/validate.py`.

| Event | Nav passed | Nav max KL | Nav min KS p | Cumulative passed | Cumulative max KL | Cumulative min KS p |
|---|---:|---:|---:|---:|---:|---:|
| `gamma_100mev` | true | 0 | 1 | true | 0 | 1 |
| `muon_10gev` | true | 0 | 1 | true | 0 | 1 |
| `nbar_carbon` | true | 0 | 1 | true | 0 | 1 |
| `cosmic_shower` | true | 0 | 1 | true | 0 | 1 |
| `optical_scintillator` | true | 0 | 1 | true | 0 | 1 |
| `beam_neutron` | true | 0 | 1 | true | 0 | 1 |

All validation comparisons passed with zero observed KL divergence and KS
p-value 1.0 for every observable.

## Remaining Phase 5 status

- 5d.1 through 5d.4 have positive speedup and validation evidence.
- The cumulative >=1.8x/no-regression acceptance gate is now satisfied locally.
- A full GPU-node CTest should be run for this 5d.4 head before declaring the
  lane complete, matching the gate used after 5d.1--5d.3.
