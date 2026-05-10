# G4GPU Validation Framework

This document defines the validation test suite required before any physics claim
can be published. All tests compare G4GPU output against Geant4 reference using
rigorous statistical tests. Plots from this suite form the core of the paper.

## Statistical standards

Every distribution comparison uses:
- **Kolmogorov-Smirnov test** — p-value > 0.05 required (null: same distribution)
- **Mean agreement** — within 1σ of Monte Carlo statistical uncertainty
- **RMS agreement** — within 2σ
- N_events ≥ 10,000 for each comparison point (to keep MC stat below 1%)

Systematic uncertainties from physics approximations are quoted separately:
- Bethe-Bloch: ±0.5% from Barkas/Bloch corrections omitted
- Highland MCS: ±2% from single-Gaussian approximation vs. Molière
- Optical: ±5% from Rayleigh angular distribution approximation

---

## V1: Muon ionization (Bethe-Bloch)

**Goal:** Verify `BetheBloch()` device function against PDG reference data and Geant4.

**Setup:** 10,000 muons per energy point, straight track in 100mm iron slab.

**Energy scan:** 100 MeV, 500 MeV, 1 GeV, 5 GeV, 10 GeV, 100 GeV, 1 TeV.

**Observables:**
- Mean dE/dx (MeV/mm) — compare to PDG muon stopping power table
- dE/dx distribution width (Landau straggling) — KS test vs. Geant4
- Range in iron (mm) — integrate dE/dx, compare to PDG range table

**Acceptance:**
- Mean dE/dx within 1% of PDG at all energies
- KS p-value > 0.05 for Landau distribution at each energy
- Range within 2% of PDG

---

## V2: Multiple Coulomb scattering

**Goal:** Verify Highland formula against Geant4 and Molière theory.

**Setup:** 10,000 muons per energy point, 10cm iron, initial direction (0,0,1).

**Energy scan:** 100 MeV, 1 GeV, 10 GeV, 100 GeV.

**Observables:**
- Projected angle θ_x distribution — KS test vs. Geant4
- theta_0 (Gaussian width) — compare to Highland formula prediction
- Non-Gaussian tail fraction (|θ| > 3θ_0) — compare to Geant4

**Acceptance:**
- theta_0 within 2% of Highland prediction
- KS p-value > 0.05 for central Gaussian
- Tail fraction within 20% of Geant4 (Highland is known to underestimate tails)

---

## V3: Muon range and bragg peak

**Goal:** End-to-end muon transport test — range = integral over all steps.

**Setup:** 10,000 muons per energy, fired into semi-infinite iron. Measure range (depth where track stops).

**Energy scan:** 50 MeV to 1 TeV (10 points log-spaced).

**Plot:** Range–energy curve (log-log) overlaid with PDG reference.

**Acceptance:** Range within 2% of PDG at all energies.

---

## V4: Voxel geometry accuracy

**Goal:** Verify voxel material lookup agrees with exact G4Navigator.

**Setup:** NNBAR detector geometry. 100,000 random points uniformly sampled in bounding box.

**Method:**
- G4GPU: look up material_id at each point via 3DDA
- Geant4: `G4Navigator::LocateGlobalPointAndSetup()` at same points
- Count disagreements

**Voxel resolutions tested:** 10mm, 5mm, 2mm, 1mm, 0.5mm.

**Acceptance:** 100% agreement at 1mm. Disagreement fraction plotted vs. resolution.

**Note:** Expected disagreements at boundaries — report boundary-crossing error fraction separately.

---

## V5: RTX geometry accuracy (when implemented)

Same as V4 but comparing RTX backend vs. G4Navigator.

**Expected:** 100% agreement (RTX uses exact triangle meshes, not voxels).

**Additional check:** Distance-to-boundary comparison at 10,000 random ray origins/directions.
Accept: |d_RTX - d_G4| < 0.01mm at 99.9% of rays.

---

## V6: Optical photon transport

**Goal:** Verify OptiX optical kernel against Geant4's G4OpBoundaryProcess.

**Setup:** Monochromatic photons (420nm, typical scintillation peak) in NNBAR scintillator geometry.

**Observables:**
- Detection efficiency (fraction reaching PMT cathode) — compare to Geant4
- Path length distribution — KS test
- Time-of-arrival distribution at PMT — KS test (important for timing resolution)
- Angular distribution at PMT cathode — KS test

**Acceptance:**
- Detection efficiency within 2% of Geant4
- KS p-value > 0.05 for path length and timing distributions

---

## V7: Full event validation (end-to-end)

**Goal:** Compare G4GPU full event (all components) against full Geant4 event.

**Setup:** 10 GeV cosmic muon entering NNBAR detector. 10,000 events each.

**Observables per sub-detector:**
- Total energy deposit (mean ± σ) — KS test
- Hit multiplicity — KS test
- Hit position distribution — 2D KS test (x-y) per layer

**Acceptance:** KS p-value > 0.05 for all observables in all sub-detectors.

---

## Performance benchmarks (for paper figures)

### B1: Throughput vs. batch size

Vary batch size N = 1K, 2K, 4K, 8K, 16K, 32K, 64K, 128K, 256K.
Measure: track-steps per second on A100.
Plot: throughput curve — find the knee (memory bandwidth limited).

### B2: Speedup vs. Geant4

For each physics component:
- G4GPU throughput (track-steps/sec)
- Geant4 throughput (same, CPU, same machine)
- Speedup factor = ratio

Report: muon step speedup, EM shower speedup, optical photon speedup.

### B3: GPU hardware utilization

Use NVIDIA Nsight Compute:
- Memory bandwidth utilization (target: >70% of A100 peak)
- SM occupancy (target: >50%)
- Arithmetic intensity (FLOP/byte) — determines if compute or bandwidth limited

### B4: End-to-end event speedup

Full NNBAR cosmic event: G4GPU vs. Geant4.
Measure wall-clock time per event.
Report: geometric mean speedup over 10,000 events.

### B5: Scaling with GPU model

Test on: V100, A100, RTX 3090 (if available).
Plot: throughput vs. peak memory bandwidth per GPU — expect linear scaling.

---

## Output format

Each test produces:
1. A ROOT file with histograms: `tests/output/V{N}_{test_name}.root`
2. A JSON summary: `{"test": "V1", "status": "PASS", "ks_pvalue": 0.42, ...}`
3. A PNG figure: `tests/figures/V{N}_{observable}.png` (paper-ready)

All figures use: matplotlib + mplhep style (CMS/ATLAS publication style).
x-axis: physical quantity with units. y-axis: normalized counts or ratio.
Ratio panel below each histogram: G4GPU/Geant4 ± statistical uncertainty.

---

## CI integration

Every pull request runs:
- V1 at 1 GeV only (fast, ~30 seconds on GPU)
- V4 at 2mm voxel only (fast, CPU-only)

Full validation suite (V1–V7 + benchmarks) runs before each tagged release.
