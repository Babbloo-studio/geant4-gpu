# V7 full-event validation scaffold

This directory is the scaffold for **V7: Full event validation (end-to-end)**
from `docs/VALIDATION.md`.  It compares a standalone G4GPU full-event output
against a vanilla Geant4 reference for an NNBAR-shaped 10 GeV cosmic-muon
workload.  This compact iteration only creates the harness design, comparison
runner skeleton, and gated SLURM entry point; it does **not** run the 10,000
-event validation campaign.

## Isolation boundary

The V7 harness treats the detector shape as data.  It may describe the
sub-detector inventory needed for histograms, but it must not import detector
production Python, include production C++ headers, or link production libraries.
All candidate outputs remain research-only until a later parity gate signs off
physics agreement.

## Primary specification

- Primary: single 10 GeV cosmic muon entering the detector envelope from the
  cosmic-veto side.
- Statistics: 10,000 G4GPU candidate events and 10,000 vanilla Geant4 reference
  events for the final validation run.
- Event selection: same random-seed manifest and same primary kinematic window
  for both backends once the real readers are implemented.
- Run root: relative paths resolve under `--run-root`, `G4GPU_V7_RUN_ROOT`, or
  the SLURM submit directory used by `submit_v7.slurm`.
- Output paths used by the scaffold, relative to that run root:
  - Candidate ROOT/Parquet: `output/v7_g4gpu.root`
  - Reference ROOT/Parquet: `output/v7_geant4_ref.root`
  - JSON summary: `output/v7_summary.json`

## Sub-detector observables

The runner groups entries by sub-detector and, where the input provides it, by
layer.  The required V7 observables are:

1. **Per-sub-detector total energy deposit** in MeV.
2. **Hit multiplicity** per event.
3. **Hit position distribution** in the transverse `x-y` plane, evaluated per
   layer when layer labels exist.

The initial sub-detector vocabulary is deliberately data-level and can be
extended by the real reader implementation: `tpc`, `scintillator`, `lead_glass`,
`cosmic_veto`, `beampipe`, `target`, and `passive_shield`.

## Statistical acceptance

For every observable group listed above:

- Kolmogorov-Smirnov p-value must be greater than `0.05`.
- Candidate/reference mean difference must be within `1σ` of the combined
  Monte Carlo statistical uncertainty.
- Candidate/reference RMS difference must be within `2σ` of the combined RMS
  statistical uncertainty.
- All required sub-detectors must be present in both candidate and reference
  inputs.

The JSON summary contains one row per observable group with the fields
`test`, `observable`, `status`, `ks_pvalue`, `mean_delta`, and `rms_delta`.
Additional diagnostic fields may be present for later plotting.

## Explicit failure modes

The runner must return nonzero when any of the following occur:

- Input file format is unsupported.
- ROOT or Parquet branch mapping has not yet been implemented.
- The configured run root or JSON output directory is not writable.
- Candidate/reference sub-detector or layer groups do not match.
- Any required observable has fewer than two finite entries in either sample.
- Any KS, mean, or RMS acceptance tolerance fails.
- The JSON summary cannot be written.

The current scaffold intentionally raises `NotImplementedError` when asked to
load ROOT or Parquet event data.  That is the expected post-commit shakedown
result; the next implementation unit wires the actual readers and then enables
the 10,000-event V7 run.
