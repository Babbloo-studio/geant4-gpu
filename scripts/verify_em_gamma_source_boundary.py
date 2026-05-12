#!/usr/bin/env python3
"""Verify EM/gamma source boundaries stay isolated and fail-closed."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOTS = (ROOT / "include", ROOT / "src", ROOT / "tests")
CMAKE = ROOT / "CMakeLists.txt"
STATIC = ROOT / "scripts/verify_em_gamma_static_contract.py"
CHAIN = ROOT / "docs/reports/em_gamma_preflight_chain_audit_20260512.md"
INDEX = ROOT / "docs/reports/em_gamma_preflight_contract_index_20260512.md"
REPORT = ROOT / "docs/reports/em_gamma_source_boundary_20260512.md"
SELF = Path(__file__)
TEXT_SUFFIXES = {".cc", ".cu", ".cuh", ".hh", ".h", ".hpp", ".txt", ".md", ".py"}
FORBIDDEN_SOURCE_MARKERS = (
    "NN" "BAR" + "_Detector",
    "nnbar" + "_reconstruction",
    "G4GPUEMPhysicsTables",
    "G4GPUEMSecondaryBuffer",
    "G4GPUEMRngStream",
    "G4GPUEMProcessSelector",
    "G4GPUEMStatusCode",
    "EMPhysicsTableView",
    "secondary_buffer",
    "rng_stream",
    "process_selector",
    "SelectEMProcess",
)


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


def iter_source_files() -> list[Path]:
    files: list[Path] = []
    for root in SOURCE_ROOTS:
        for path in root.rglob("*"):
            if path.is_file() and path.suffix in TEXT_SUFFIXES:
                files.append(path)
    return sorted(files)


def main() -> int:
    for path in iter_source_files():
        body = text(path)
        for marker in FORBIDDEN_SOURCE_MARKERS:
            if marker in body:
                raise SystemExit(
                    f"forbidden source-boundary marker {marker!r} in {path.relative_to(ROOT)}"
                )

    for marker in (
        "No `G4GPUEMPhysicsTables` implementation exists",
        "No `G4GPUEMSecondaryBuffer` implementation exists",
        "No `G4GPUEMRngStream`, `G4GPUEMProcessSelector`, or `G4GPUEMStatusCode`",
        "No detector/event workload",
    ):
        require(CHAIN, marker)
    for marker in (
        "Table owner",
        "Secondary buffer",
        "RNG stream",
        "Process selector",
        "Status code vocabulary",
    ):
        require(INDEX, marker)

    for marker in (
        "source-boundary verifier scans the EM/gamma implementation roots",
        "Guarded absent implementations",
        "must not enter the source\nroots before the matching preflight contract",
        "does not authorize SLURM submission",
    ):
        require(REPORT, marker)

    for marker in (
        "NAME g4gpu_em_source_boundary",
        "scripts/verify_em_gamma_source_boundary.py",
    ):
        require(CMAKE, marker)
        require(STATIC, marker)

    for path in (CMAKE, STATIC, REPORT, SELF):
        for forbidden in ("NN" "BAR" + "_Detector", "nnbar" + "_reconstruction"):
            require_absent(path, forbidden)

    print("EM_GAMMA_SOURCE_BOUNDARY_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
