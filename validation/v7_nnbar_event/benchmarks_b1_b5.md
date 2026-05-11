# B1-B5 performance benchmark scaffold

This document scopes the paper-facing performance measurements from
`docs/VALIDATION.md`.  It is a plan only: no throughput sweep is launched in
this compact V7 scaffold.

## Shared controls

- Candidate backend: G4GPU build and commit under test.
- Reference backend: vanilla Geant4 on the same site and input event family.
- Event family: full NNBAR-shaped 10 GeV cosmic-muon event for end-to-end
  timing; component benchmarks may additionally use the existing phase-5
  canonical event executables.
- Statistics: 10,000 events for physics validation; performance sweeps record
  enough batches to make median and interquartile range stable.
- Report every run with commit hash, GPU model, driver/CUDA versions, compiler,
  batch size, wall time, track steps, events, and random-seed manifest.

## B1: Throughput vs. batch size

Sweep batch size
`1K, 2K, 4K, 8K, 16K, 32K, 64K, 128K, 256K`.

Metric:

- primary: track-steps per second;
- secondary: events per second and wall-clock time per event.

Acceptance plot:

- x-axis: batch size on log2 scale;
- y-axis: track-steps/s;
- show the knee where throughput stops improving and annotate memory capacity
  limits or scheduler failures.

## B2: Speedup vs. Geant4

For each physics component with an implemented G4GPU kernel, measure:

- G4GPU track-steps/s on GPU;
- Geant4 track-steps/s on CPU on the same cluster generation;
- speedup factor `G4GPU / Geant4`.

Required rows for the first complete benchmark table are muon stepping, EM
shower stepping, and optical photon transport.  Rows without implemented kernels
must be reported as `OPEN`, not silently omitted.

Acceptance plot:

- grouped bar chart of throughput and speedup by component;
- error bars from repeated batches or bootstrap resampling;
- explicit notes for unavailable kernels.

## B3: GPU hardware utilization

Use NVIDIA Nsight Compute for representative B1 batch sizes around the
throughput knee.

Targets from `docs/VALIDATION.md`:

- memory bandwidth utilization greater than `70%` of peak;
- SM occupancy greater than `50%`;
- arithmetic intensity recorded as FLOP/byte to classify bandwidth- or
  compute-limited regimes.

Acceptance plot:

- memory-bandwidth and SM-occupancy bars by kernel;
- roofline-style annotation when arithmetic intensity is available.

## B4: End-to-end event speedup

Run the full NNBAR-shaped cosmic-muon event through both backends with the same
primary specification used by V7.

Metric:

- wall-clock time per event;
- geometric-mean speedup over 10,000 events;
- optional secondary metric: track-steps/s for the same event set.

Acceptance plot:

- candidate/reference time-per-event distribution;
- ratio panel for `G4GPU / Geant4` throughput;
- mark any physics-validation failure from V7 because speedup is not publishable
  without agreement.

## B5: Scaling with GPU model

Run the B1 throughput knee batch on every available GPU model.

Required models from `docs/VALIDATION.md`:

- V100;
- A100;
- RTX 3090, if available.

The local cluster may substitute A40 as an operational shakedown point, but the
paper table must keep the requested V100/A100/RTX 3090 rows open until measured
or explicitly blocked.

Acceptance plot:

- throughput vs. peak memory bandwidth per GPU;
- linear-scaling guide line;
- annotate driver, CUDA, and clock-throttling conditions.
