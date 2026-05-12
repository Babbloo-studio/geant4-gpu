# Phase 5 W5/W6 methodology alias audit

Date: 2026-05-12
Checkout: `/projects/hep/fs10/shared/nnbar/billy/geant4-gpu`

## Finding

`docs/specs/paper-methodology.md` defines:

- W5: NNBAR full event (signal), 1000 events, `FTFP_BERT`, all detector Parquet outputs.
- W6: NNBAR full event (cosmic mu), 500 events, `FTFP_BERT`, TPC hits and scintillator edep.

The current G4GPU checkout does not contain true NNBAR full-event signal or
cosmic-mu benchmark drivers. Its available Phase-5 event drivers are local
stand-ins listed in `benchmarks/events/BenchmarkDriver.hh` and wired by
`CMakeLists.txt`. The two problematic stand-ins are:

- `optical_scintillator`: 1 MeV electron in a scintillator cell.
- `beam_neutron`: 25 meV neutron in a B4C beampipe.

A read-only reference probe of the generated reference set confirmed the alias
mismatch:

```text
W5/PL1 rows=1000 event_names=['optical_scintillator']
W6/PL1 rows=1000 event_names=['beam_neutron']
```

## Fix applied

The harness now fails closed for canonical `W5` and `W6` requests. These IDs no
longer resolve to the stand-in event drivers in `benchmarks/harness/builder.py`.
Focused tests assert that dry-run/reference collection for `W5`/`W6` exits with
a methodology-blocked error instead of rendering or collecting a script.

The stand-in drivers remain available only by their explicit event names
(`optical_scintillator` and `beam_neutron`) for historical Phase-5 microbenchmark
work. That keeps old stand-in evidence usable as stand-in evidence while making
it impossible to label those files as paper-methodology W5/W6 rows.

## Superseded reference evidence

The current 480-file reference manifest remains mechanically readable, but the
`benchmarks/reference/W5/*` and `benchmarks/reference/W6/*` subsets are
superseded for methodology W5/W6. They must not be promoted to paper-ready NNBAR
full-event signal/cosmic-mu references, and they must not be used to claim
speedup or parity.

OPEN: Implement true NNBAR full-event signal and cosmic-mu benchmark drivers (or
an approved isolated adapter) before restoring `W5`/`W6` resolution.

OPEN: After true drivers exist, run a separate guarded reference-regeneration
goal to replace the superseded `W5`/`W6` references and refresh the manifest.

## Boundary

No SLURM job was submitted or cancelled, no holder-node event execution was
performed, no reference Parquet was regenerated, no `benchmarks/results` row was
promoted, and no speedup/parity/paper-ready W5/W6 claim is made here.
