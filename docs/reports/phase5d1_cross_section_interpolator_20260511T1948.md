# Phase 5d.1 cross-section interpolator optimization — 2026-05-11 19:48 CEST

Lane: `g4gpu-phase5`
Subphase: `5d.1` (`src/physics/CrossSectionInterpolator.cc`)

## Summary

Implemented a CPU fallback cross-section interpolation path with runtime SIMD
dispatch. The default path selects AVX-512F, AVX2/FMA, or NEON when
available and falls back to the scalar implementation otherwise. On the
current LUNARC Milan login CPU the backend probe reports AVX2.

The benchmark drivers now exercise the interpolator through a deterministic
uniform cross-section table workload. The environment variable
`G4GPU_XS_DISABLE_SIMD=1` forces the scalar control path for A/B timing and
validation comparisons.

## Files

- `include/g4gpu/CrossSectionInterpolator.hh`
- `src/physics/CrossSectionInterpolator.cc`
- `tests/test_cross_section_interpolator.cc`
- `benchmarks/events/BenchmarkDriver.hh`
- `benchmarks/profiles/phase5d1_cross_section_avx2_20260511T1948.json`

## Focused verification

Build directory: `build_phase5d1`

```text
ctest --test-dir build_phase5d1 -R "g4gpu_cross_section_interpolator|g4gpu_benchmark_manifest|g4gpu_benchmark_script_syntax|g4gpu_validate_harness|g4gpu_benchmark_.*_smoke" --output-on-failure
100% tests passed, 0 tests failed out of 10
```

Backend probe:

```text
PASS: cross-section interpolation backend=avx2, max_abs=0
```

## Scalar vs SIMD benchmark evidence

Each event used 10,000 generated events and seven repetitions. Timings are
the benchmark driver `total_wall_time_ns` field, which covers row generation
and the cross-section interpolation workload but not Parquet conversion.

| Event | Scalar median ns | SIMD median ns | Speedup |
|---|---:|---:|---:|
| `gamma_100mev` | 19172509 | 15530136 | 1.235x |
| `muon_10gev` | 19159525 | 15387058 | 1.245x |
| `nbar_carbon` | 19269962 | 15384393 | 1.253x |
| `cosmic_shower` | 18895268 | 15296317 | 1.235x |
| `optical_scintillator` | 19005565 | 15245482 | 1.247x |
| `beam_neutron` | 19053155 | 15391887 | 1.238x |

All six event drivers show positive scalar-to-SIMD speedup for 5d.1. This
does not yet satisfy the full Phase 5 acceptance target of at least 1.8x on
four events; that target remains open for the cumulative 5d stack.

## Validation evidence

For each event, 1,000-event scalar and SIMD Parquet outputs were compared
with `benchmarks/validate.py` using the existing four observables. Results:

| Event | Passed | Max KL | Min KS p-value |
|---|---:|---:|---:|
| `gamma_100mev` | true | 0 | 1 |
| `muon_10gev` | true | 0 | 1 |
| `nbar_carbon` | true | 0 | 1 |
| `cosmic_shower` | true | 0 | 1 |
| `optical_scintillator` | true | 0 | 1 |
| `beam_neutron` | true | 0 | 1 |

All validation comparisons passed with zero observed KL divergence and
KS p-value 1.0 for every observable, as expected for an algebraically
equivalent interpolation path.

## Remaining Phase 5 status

- 5d.1 has positive speedup and validation evidence and is eligible to commit.
- 5d.2 branchless surface tests, 5d.3 aligned tracks, and 5d.4 navigation
  prefetch remain unstarted.
- Full Phase 5 DONE is still blocked until the cumulative 5d stack reaches
  the required speedup and no-regression gates.
