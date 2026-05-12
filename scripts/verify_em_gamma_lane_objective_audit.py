#!/usr/bin/env python3
"""Verify the EM/gamma lane objective is mapped to concrete artifacts."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs/reports/em_gamma_lane_objective_audit_20260512.md"
HEADER = ROOT / "include/g4gpu/EMStepKernel.hh"
KERNEL = ROOT / "src/physics/EMStepKernel.cu"
TEST = ROOT / "tests/test_em_klein_nishina.cu"
CMAKE = ROOT / "CMakeLists.txt"
STATIC = ROOT / "scripts/verify_em_gamma_static_contract.py"
SELF = Path(__file__)
LINE_CAP_PATHS = (
    HEADER,
    KERNEL,
    TEST,
    CMAKE,
    SELF,
    REPORT,
)
SOURCE_ROOTS = (ROOT / "include", ROOT / "src", ROOT / "tests")
TEXT_SUFFIXES = {".cc", ".cu", ".cuh", ".hh", ".h", ".hpp", ".txt", ".md", ".py"}


def text(path: Path) -> str:
    if not path.exists():
        raise SystemExit(f"missing required file: {path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8", errors="replace")


def require(path: Path, needle: str) -> None:
    if needle not in text(path):
        raise SystemExit(f"missing marker in {path.relative_to(ROOT)}: {needle}")


def require_absent(path: Path, needle: str) -> None:
    if needle in text(path):
        raise SystemExit(f"unexpected marker in {path.relative_to(ROOT)}: {needle}")


def line_count(path: Path) -> int:
    return len(text(path).splitlines())


def iter_source_files() -> list[Path]:
    files: list[Path] = []
    for root in SOURCE_ROOTS:
        for path in root.rglob("*"):
            if path.is_file() and path.suffix in TEXT_SUFFIXES:
                files.append(path)
    return sorted(files)


def main() -> int:
    for marker in (
        "EMStep(",
        "LaunchEMStepKernel",
        "LaunchComptonSampleKernel",
        "SamplePhotoelectric",
        "SampleCompton",
        "SamplePair",
        "SampleBremsstrahlung",
    ):
        require(HEADER, marker)

    for marker in (
        "Kahn/Butcher-Messel rejection sampler",
        "SampleKleinNishinaEnergyFraction",
        "TODO Phase 2.EM-photoelectric",
        "TODO Phase 2.EM-pair",
        "TODO Phase 2.EM-bremsstrahlung",
    ):
        require(KERNEL, marker)

    for marker in (
        "constexpr int kSamples = 10000;",
        "constexpr double kRequiredPValue = 0.05;",
        "constexpr int kCudaUnavailableSkipCode = 77;",
        "PASS: Klein-Nishina scattered-energy KS",
    ):
        require(TEST, marker)

    for marker in (
        "if(G4GPU_WITH_EM)",
        "target_sources(G4GPU PRIVATE src/physics/EMStepKernel.cu)",
        "target_link_libraries(G4GPU PRIVATE CUDA::curand)",
        "NAME g4gpu_em_klein_nishina",
        "NAME g4gpu_em_lane_objective_audit",
        "scripts/verify_em_gamma_lane_objective_audit.py",
    ):
        require(CMAKE, marker)
        if marker.startswith("NAME ") or marker.startswith("scripts/"):
            require(STATIC, marker)

    for path in LINE_CAP_PATHS:
        if line_count(path) > 500:
            raise SystemExit(f"line cap exceeded: {path.relative_to(ROOT)}")

    for path in iter_source_files():
        for forbidden in ("NN" "BAR" + "_Detector", "nnbar" + "_reconstruction"):
            require_absent(path, forbidden)

    for marker in (
        "Prompt-to-artifact checklist",
        "Header interface exists under `include/g4gpu/EMStepKernel.hh`",
        "Klein-Nishina validation fixture exists",
        "Current fallback publication is fresh",
        "Remaining EM processes are not falsely promoted",
        "does not authorize SLURM submission",
    ):
        require(REPORT, marker)

    for path in (REPORT, SELF, CMAKE, STATIC):
        for forbidden in ("NN" "BAR" + "_Detector", "nnbar" + "_reconstruction"):
            require_absent(path, forbidden)

    print("EM_GAMMA_LANE_OBJECTIVE_AUDIT_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
