# W5/W6 full-event driver plan

Date: 2026-05-12
Status: fail-closed implementation scaffold; no event execution or reference
regeneration is authorized by this document.

## Methodology target

`docs/specs/paper-methodology.md` in the NNBAR coordination checkout defines
two publication workloads that are not present as true drivers in this G4GPU
checkout yet:

| ID | Required event | Events | Physics list | Required output |
|----|----------------|--------|--------------|-----------------|
| W5 | NNBAR full event (signal) | 1000 | FTFP_BERT | all detector Parquet outputs |
| W6 | NNBAR full event (cosmic mu) | 500 | FTFP_BERT | TPC hits and scintillator energy deposition |

The current `optical_scintillator` and `beam_neutron` drivers are stand-ins.
They must stay addressable only by explicit event name and must not regain the
canonical `W5`/`W6` aliases.

## Isolation boundary

The future W5/W6 implementation must keep G4GPU isolated from NNBAR production:

1. Do not include, compile, or link NNBAR detector headers/libraries in G4GPU.
2. Do not copy NNBAR production source into this repo.
3. Use a compute-node-only adapter that shells out to an approved vanilla NNBAR
   executable and macro path, with every command rendered by the harness and
   visible in the sbatch script.
4. Store only benchmark harness metadata, normalized observables, and checksums
   in G4GPU; detector output Parquets remain external raw/reference artifacts.
5. Keep `W5`/`W6` fail-closed until preflight evidence verifies the exact
   executable, macro, physics list, output schema, seed list, and row counts.

## Driver scaffold contract

A future implementation should add two workload specs only after the preflight
below is green:

| ID | Proposed workload name | Adapter command purpose |
|----|------------------------|-------------------------|
| W5 | `nnbar_signal_full_event` | run the approved nbar-carbon signal macro and normalize all detector outputs |
| W6 | `nnbar_cosmic_mu_full_event` | run the approved cosmic-mu macro and normalize TPC/scintillator outputs |

Each adapter must write one raw harness Parquet per seed with at least the
columns already consumed by `benchmarks.harness.parity`: `event_name`,
`total_deposited_energy_mev`, `step_count`, `particle_multiplicity`,
`first_step_length_mm`, `total_wall_time_ns`, and `per_step_time_ns`. For W6,
`neutron_capture_rate` is not required unless the final cosmic-mu macro records
neutron observables.

## Required preflight evidence before enabling aliases

- `NNBAR_EXECUTABLE`: executable path exists, is executable, and is outside the
  G4GPU build tree.
- `NNBAR_MACRO_W5` / `NNBAR_MACRO_W6`: macro paths exist and pin FTFP_BERT.
- `NNBAR_OUTPUT_SCHEMA`: detector Parquet files include the columns needed to
  derive the harness observables.
- `NNBAR_EVENT_COUNT`: W5 adapter enforces 1000 events; W6 enforces 500 events.
- `NNBAR_SEEDS`: exactly the harness seed set is passed through to the macro or
  recorded as a blocker if the macro cannot accept deterministic seeds.
- `NNBAR_ISOLATION_OK`: grep/build checks show no G4GPU include/link has been
  added to NNBAR, and no NNBAR include/link has been added to G4GPU.

If any item is missing, `resolve_workload("W5")` and `resolve_workload("W6")`
must continue to raise the methodology-blocked error.

## Later guarded regeneration sequence

1. Add adapter preflight tests with fixture-only paths; no detector execution.
2. Add dry-run sbatch rendering for `W5` and `W6`; require `bash -n` and
   `sbatch --test-only` evidence only.
3. Run one explicit, planner-approved guarded reference-regeneration goal for
   W5/W6; do not combine it with code changes.
4. Read back all generated reference Parquets, check row counts and event names,
   refresh `benchmarks/reference/MANIFEST.sha256`, and mark the old W5/W6
   stand-in subsets superseded.
5. Only after the regenerated references are readable may later optimization
   measurement goals append `benchmarks/results/results.parquet` rows.

This document authorizes no SLURM submission, event execution, reference
regeneration, speedup claim, parity claim, or paper-ready W5/W6 claim.
