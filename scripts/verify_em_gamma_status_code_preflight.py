#!/usr/bin/env python3
"""Verify the EM/gamma status-code preflight stays fail-closed."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs/reports/em_gamma_status_code_preflight_20260512.md"
HEADER = ROOT / "include/g4gpu/EMStepKernel.hh"
KERNEL = ROOT / "src/physics/EMStepKernel.cu"
TEST = ROOT / "tests/test_em_klein_nishina.cu"
STUB = ROOT / "scripts/verify_em_gamma_stub_fail_closed.py"
TABLE = ROOT / "docs/reports/em_gamma_table_owner_preflight_20260512.md"
RNG = ROOT / "docs/reports/em_gamma_rng_stream_preflight_20260512.md"
SECONDARY = ROOT / "docs/reports/em_gamma_secondary_buffer_preflight_20260512.md"
SELECTOR = ROOT / "docs/reports/em_gamma_process_selector_preflight_20260512.md"
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
        "G4GPUEMStatusCode",
        "off-by-default",
        "Named status vocabulary",
        "No silent mutation contract",
        "Host visibility contract",
        "Compatibility contract",
        "Documentation contract",
        "status == 0",
        "missing table",
        "missing RNG",
        "secondary overflow",
        "unsupported particle",
        "validation-only slow path",
        "do not\nmutate tracks",
        "physics-parity claims",
        "speedup claims",
    ):
        require(REPORT, marker)

    for marker in (
        "int status = 0;",
        "EMInteractionResult",
        "EMProcess process",
    ):
        require(HEADER, marker)
    for marker in (
        "result.status == 0",
        "tracks.status[i] = result.status",
        "out = {};",
    ):
        require(KERNEL, marker)
    require(TEST, "PASS: Klein-Nishina scattered-energy KS")
    require(STUB, "out.status = 0")

    for report, marker in (
        (TABLE, "labelled fail-closed status"),
        (RNG, "labelled fail-closed status"),
        (SECONDARY, "labelled fail-closed status code"),
        (SELECTOR, "Fallback/slow-path contract"),
    ):
        require(report, marker)

    for forbidden in (
        "G4GPUEMStatusCode",
        "enum class EMStatus",
        "status_code",
    ):
        require_absent(HEADER, forbidden)
        require_absent(KERNEL, forbidden)

    for marker in (
        "NAME g4gpu_em_status_code_preflight",
        "scripts/verify_em_gamma_status_code_preflight.py",
    ):
        require(CMAKE, marker)
        require(STATIC, marker)

    for path in (REPORT, HEADER, KERNEL, TEST, CMAKE, STATIC, SELF):
        for forbidden in ("NN" "BAR" + "_Detector", "nnbar" + "_reconstruction"):
            require_absent(path, forbidden)

    print("EM_GAMMA_STATUS_CODE_PREFLIGHT_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
