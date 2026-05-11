# Phase 5 measurement-framework audit

Date: 2026-05-11 17:20 CEST  
Lane: `g4gpu-phase5`  
Branch: `lane/g4gpu-phase5`  
Implementation commits: `57800c2` + `1e36431`  
Profiled benchmark commit: `57800c2`

## Objective restatement

The current lane objective is to establish the Phase 5 measurement framework
before any L0 microarchitecture optimization starts.  Concretely, the required
framework artifacts are:

1. six benchmark event drivers that emit Parquet output on LUNARC;
2. `benchmarks/run_baseline.sh` to build/run the suite through SLURM;
3. CPU and GPU profiling harness entry points;
4. committed `perf report` / `perf annotate` text for the six benchmark events;
5. `benchmarks/validate.py` with KS + KL gates over the required observables;
6. LUNARC build/test evidence; and
7. no Phase 5d optimization work before planner review.

The full Phase 5 acceptance also contains future L0 requirements (>=1.8x CPU
speedup on at least four events and no validation regression).  Those are not
claimed here because the lane stop condition says to stop after 5a--5c and wait
for planner review before starting 5d.

## Prompt-to-artifact checklist

| Requirement | Artifact/evidence inspected | Status |
| --- | --- | --- |
| Read strategy root | `docs/specs/g4gpu-line-by-line-acceleration.md` re-read from the NNBAR repo before this audit | PASS |
| Work on `lane/g4gpu-phase5` | `git status --short --branch` in geant4-gpu shows `lane/g4gpu-phase5...origin/lane/g4gpu-phase5 [ahead 2]` before this audit commit | PASS |
| Six event drivers exist | `benchmarks/events/{gamma_100mev,muon_10gev,nbar_carbon,cosmic_shower,optical_scintillator,beam_neutron}.cc` | PASS |
| Stand-in geometry committed | `benchmarks/geometries/README.md` and `benchmarks/geometries/StandInGeometry.hh` define local isolated fixtures | PASS |
| Drivers run 1000 events by default | `BenchmarkEventSpec::default_events = 1000` and manifest CTest asserts each event has default 1000 | PASS |
| Records wall time | Parquet schema includes `total_wall_time_ns` | PASS |
| Records per-step time | Parquet schema includes `per_step_time_ns` | PASS |
| Records hits histogram input | Parquet schema includes `hits` and `hit_bin` | PASS |
| Records primary kinematics | Parquet schema includes `primary_pdg`, `primary_ke_mev`, and primary momentum components | PASS |
| Produces Parquet under `benchmarks/results/<event>_<commit>.parquet` | LUNARC job `3041865` produced all six `*_57800c2.parquet` files | PASS |
| `run_baseline.sh` orchestrator exists | `benchmarks/run_baseline.sh` builds on LUNARC, submits SLURM, runs all six, and also records canonical Geant4 example logs | PASS |
| Canonical Geant4 examples included per strategy doc | `benchmarks/canonical/CanonicalExamples.hh`; `canonical_examples_57800c2.csv` contains B1, TestEm0, Hadr01, Hadr02, OpNovice2, Par01 | PASS |
| CPU profiler exists | `benchmarks/profile_cpu.sh` wraps each event in `perf record`, emits report + top-20 annotate text | PASS |
| CPU annotate output committed for each event | Commit `1e36431` added six `benchmarks/profiles/*_cpu_57800c2.txt` files; each has one report and 20 annotate sections | PASS |
| GPU profiler exists | `benchmarks/profile_gpu.sh` wraps events in `ncu --set full --target-processes all` | IMPLEMENTED / RUNTIME PENDING |
| Validator exists | `benchmarks/validate.py` loads two Parquet files, runs KS and binned KL checks | PASS |
| Validator observables cover required list | Self-test JSONs cover total deposited energy, leading particle KE, particle multiplicity, and vertex-position radius | PASS |
| KL tolerance <= 1% | `validate.py` default `--kl-tolerance` is `0.01` | PASS |
| Nonzero on tolerance breach | `benchmarks/tools/validate_self_test.py` creates shifted data and asserts the comparison fails | PASS |
| CI/CTest gate exists | CMake adds `g4gpu_validate_harness`, `g4gpu_benchmark_script_syntax`, manifest, and six smoke tests | PASS |
| LUNARC focused CTest evidence | Focused build/CTest passed 9/9: manifest, script syntax, validate harness, six benchmark smokes | PASS |
| Full GPU CTest evidence | SLURM job `3041846` is pending in `gpua40`; start estimate `2026-05-12T09:59:00` | BLOCKED |
| GitHub push | `git push origin lane/g4gpu-phase5` failed because this pane has no GitHub credentials | BLOCKED |
| Phase 5d not started | No `src/physics/CrossSectionInterpolator.cc`, `src/geometry/branchless_solids.cc`, or `include/g4gpu/Track.hh` L0 changes were made in this lane | PASS |

## LUNARC baseline evidence

`benchmarks/run_baseline.sh --on-lunarc` submitted SLURM job `3041865` for
commit `57800c2`.  The resulting Parquet files were inspected with PyArrow:

| Event | Bytes | Rows | Required columns present |
| --- | ---: | ---: | --- |
| `gamma_100mev` | 73042 | 1000 | yes |
| `muon_10gev` | 61751 | 1000 | yes |
| `nbar_carbon` | 70045 | 1000 | yes |
| `cosmic_shower` | 63093 | 1000 | yes |
| `optical_scintillator` | 81683 | 1000 | yes |
| `beam_neutron` | 73177 | 1000 | yes |

Canonical Geant4 example timing/log summary from
`benchmarks/results/canonical_examples_57800c2.csv`:

| Example | Macro | Wall time ns |
| --- | --- | ---: |
| `basic_b1` | `run1.mac` | 3240552878 |
| `testem0` | `TestEm0.in` | 1067859208 |
| `hadr01` | `hadr01.in` | 362673256 |
| `hadr02` | `hadr02.in` | 565119770 |
| `opnovice2` | `electron.mac` | 5337748957 |
| `par01` | `examplePar01.in` | 1933211730 |

## Validation evidence

`benchmarks/validate.py` was run as a Geant4-baseline sanity check by comparing
each `*_57800c2.parquet` file to itself.  Each JSON summary reported `passed:
true` with four passing observables:

- `total_deposited_energy`
- `leading_particle_ke`
- `particle_multiplicity`
- `vertex_position_radius`

This proves the harness reads the Phase 5 Parquet schema and accepts an
identical baseline.  It is not evidence of accelerated-vs-reference physics
agreement yet; that remains a Phase 5d+ gate after planner review.

## Profiling evidence

CPU profiling job `3041873` wrote all six committed profile artifacts.  Each
file contains one `perf report --stdio` section and 20 `perf annotate --stdio`
sections:

| Profile artifact | Lines | Annotate sections |
| --- | ---: | ---: |
| `benchmarks/profiles/gamma_100mev_cpu_57800c2.txt` | 11232 | 20 |
| `benchmarks/profiles/muon_10gev_cpu_57800c2.txt` | 10966 | 20 |
| `benchmarks/profiles/nbar_carbon_cpu_57800c2.txt` | 11337 | 20 |
| `benchmarks/profiles/cosmic_shower_cpu_57800c2.txt` | 11093 | 20 |
| `benchmarks/profiles/optical_scintillator_cpu_57800c2.txt` | 11082 | 20 |
| `benchmarks/profiles/beam_neutron_cpu_57800c2.txt` | 11012 | 20 |

## Publication / queue blockers

- GitHub publication is blocked in this LUNARC pane: `gh auth status` reports no
  login and `git push origin lane/g4gpu-phase5` cannot read HTTPS credentials.
- Verified fallback artifacts were created at
  `/projects/hep/fs10/shared/nnbar/billy/g4gpu-phase5-publication/`:
  - bundle sha256 `fd871b17b9e032b9f878a516e28fb1cebfdd52bfb9e00971febf1a6c3c647c0c`
  - patch sha256 `1dfe1479f3cd24bc172480ccd62675949cf7579d929aa5cde1a9a6c0eca77a70`
- Full GPU CTest job `3041846` is pending due scheduler priority.  It has been
  shortened to a 5-minute limit and currently estimates start at
  `2026-05-12T09:59:00` on `cg04`.

## Audit conclusion

Subphases 5a--5c are implemented and have CPU/LUNARC evidence sufficient for
planner review, with the two explicit external blockers above.  Phase 5 is not
DONE because 5d has not started, the full GPU CTest is pending, and GitHub push
is blocked.  Do not start L0 optimization work until planner review clears the
stop condition.
