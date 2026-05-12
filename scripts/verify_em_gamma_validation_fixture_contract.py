#!/usr/bin/env python3
"""Verify the EM/gamma validation fixture contract stays fail-closed."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs/reports/em_gamma_validation_fixture_contract_20260512.md"
ROADMAP = ROOT / "docs/reports/em_gamma_implementation_roadmap_20260512.md"
INDEX = ROOT / "docs/reports/em_gamma_deferred_contract_index_20260512.md"
CONTRACTS = (
    ROOT / "docs/reports/em_gamma_photoelectric_contract_20260512.md",
    ROOT / "docs/reports/em_gamma_pair_contract_20260512.md",
    ROOT / "docs/reports/em_gamma_bremsstrahlung_contract_20260512.md",
)
VALIDATION = ROOT / "docs/VALIDATION.md"
FIXTURE_DIR = ROOT / "docs/fixtures/em_gamma"
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
        "Reference provenance",
        "Observable declaration",
        "Statistics contract",
        "Process coverage",
        "Failure mode",
        "SHA-256 digest",
        "at least 10,000 samples",
        "p > 0.05",
        "photoelectric fixtures must cover attenuation",
        "pair-production fixtures must cover conversion",
        "bremsstrahlung fixtures must cover radiative loss",
        "No `docs/fixtures/em_gamma/` validation dataset is present",
        "not authorize SLURM submission",
        "physics-parity claims",
        "speedup claims",
    ):
        require(REPORT, marker)

    for report in CONTRACTS:
        require(report, "Geant4 or tabulated references")
        require(report, "Validation gate")
        require(report, "p > 0.05")

    for marker in (
        "GPU validation and publication",
        "Geant4/tabulated references",
        "archived logs",
        "sacct",
    ):
        require(ROADMAP, marker)

    for marker in (
        "g4gpu_em_photoelectric_contract",
        "g4gpu_em_pair_contract",
        "g4gpu_em_bremsstrahlung_contract",
    ):
        require(INDEX, marker)

    require(VALIDATION, "Kolmogorov-Smirnov test")
    require(VALIDATION, "N_events ≥ 10,000")

    if FIXTURE_DIR.exists():
        raise SystemExit(
            "unexpected live EM/gamma fixture directory without a verifier update: "
            f"{FIXTURE_DIR.relative_to(ROOT)}"
        )

    for marker in (
        "NAME g4gpu_em_validation_fixture_contract",
        "scripts/verify_em_gamma_validation_fixture_contract.py",
    ):
        require(CMAKE, marker)
        require(STATIC, marker)

    for path in (REPORT, ROADMAP, INDEX, CMAKE, STATIC, SELF):
        for forbidden in ("NN" "BAR" + "_Detector", "nnbar" + "_reconstruction"):
            require_absent(path, forbidden)

    print("EM_GAMMA_VALIDATION_FIXTURE_CONTRACT_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
