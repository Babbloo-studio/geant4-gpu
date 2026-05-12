#!/usr/bin/env python3
"""Verify the EM/gamma RNG-stream preflight stays fail-closed."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs/reports/em_gamma_rng_stream_preflight_20260512.md"
ROADMAP = ROOT / "docs/reports/em_gamma_implementation_roadmap_20260512.md"
SECONDARY = ROOT / "docs/reports/em_gamma_secondary_buffer_preflight_20260512.md"
HEADER = ROOT / "include/g4gpu/EMStepKernel.hh"
KERNEL = ROOT / "src/physics/EMStepKernel.cu"
TEST = ROOT / "tests/test_em_klein_nishina.cu"
CMAKE = ROOT / "CMakeLists.txt"
STATIC = ROOT / "scripts/verify_em_gamma_static_contract.py"
SELF = Path(__file__)


def text(path: Path) -> str:
    if not path.exists():
        raise SystemExit(f"missing required file: {path.relative_to(ROOT)}")
    return path.read_text()


def require(path: Path, needle: str) -> None:
    if needle not in text(path):
        raise SystemExit(f"missing marker in {path.relative_to(ROOT)}: {needle}")


def require_absent(path: Path, needle: str) -> None:
    if needle in text(path):
        raise SystemExit(
            f"unexpected marker in {path.relative_to(ROOT)}: {needle}"
        )


def main() -> int:
    for marker in (
        "G4GPUEMRngStream",
        "off-by-default",
        "Owner contract",
        "Seed provenance contract",
        "Consumption contract",
        "Replay contract",
        "Missing-RNG gate",
        "labelled fail-closed status",
        "does not mutate primary tracks",
        "secondary buffers",
        "physics-parity claims",
        "speedup claims",
    ):
        require(REPORT, marker)

    for marker in (
        "curandState*",
        "one `curandState*` per track or\nsample",
        "fixed seed",
        "variable numbers of uniforms",
    ):
        require(REPORT, marker)

    for marker in (
        "curandState*: one RNG state per track/sample",
        "LaunchComptonSampleKernel",
        "SamplePhotoelectric",
        "SamplePair",
        "SampleBremsstrahlung",
    ):
        require(HEADER, marker)
    for marker in (
        "curandState local_rng{}",
        "const bool stochastic = rng != nullptr",
        "if (stochastic) rng[i] = local_rng",
        "Uniform(curandState* rng)",
    ):
        require(KERNEL, marker)
    for marker in (
        "curand_init(seed, i, 0, &rng[i])",
        "20260511ULL",
        "constexpr int kSamples = 10000;",
        "PASS: Klein-Nishina scattered-energy KS",
    ):
        require(TEST, marker)

    for marker in (
        "Owned secondary buffer",
        "Process-selection contract",
    ):
        require(ROADMAP, marker)
    require(SECONDARY, "G4GPUEMSecondaryBuffer")

    for forbidden in ("G4GPUEMRngStream", "rng_stream", "EMRngStream"):
        require_absent(HEADER, forbidden)
        require_absent(KERNEL, forbidden)

    for marker in (
        "NAME g4gpu_em_rng_stream_preflight",
        "scripts/verify_em_gamma_rng_stream_preflight.py",
    ):
        require(CMAKE, marker)
        require(STATIC, marker)

    for path in (REPORT, ROADMAP, SECONDARY, HEADER, KERNEL, TEST, CMAKE, STATIC, SELF):
        for forbidden in ("NN" "BAR" + "_Detector", "nnbar" + "_reconstruction"):
            require_absent(path, forbidden)

    print("EM_GAMMA_RNG_STREAM_PREFLIGHT_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
