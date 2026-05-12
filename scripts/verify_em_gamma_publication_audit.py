#!/usr/bin/env python3
"""Verify the EM/gamma current-publication audit remains fail-closed."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs/reports/em_gamma_current_publication_audit_20260512.md"
CMAKE = ROOT / "CMakeLists.txt"
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


def require_count(path: Path, needle: str, minimum: int) -> None:
    count = text(path).count(needle)
    if count < minimum:
        raise SystemExit(
            f"expected at least {minimum} occurrences of {needle!r} in "
            f"{path.relative_to(ROOT)}, found {count}"
        )


def main() -> int:
    for marker in (
        "# EM/gamma current-publication audit",
        "audited subject head",
        "ac6a00e1d9d31817eb064f292f2e7fda3f2a9d62",
        "fork_ref=ac6a00e1d9d31817eb064f292f2e7fda3f2a9d62",
        "Current-head\nartifact freshness is delegated to `g4gpu_em_publication_artifacts`",
        "head-sensitive and must fail until each later commit",
        "Current-head publication freshness",
        "g4gpu_em_publication_artifacts",
        "EM_GAMMA_CURRENT_AC6A00E_OK",
        "EM_GAMMA_RUNTIME_GATE_OK",
        "g4gpu_em_klein_nishina skipped",
        "No new SLURM command",
        "GPU runtime test",
        "NNBAR production edit",
        "speedup claim",
        "physics-parity claim",
        "ABI migration",
        "photoelectric, pair-production, and bremsstrahlung",
        "lane-g4gpu-em-gamma-ac6a00e.bundle",
        "SHA256SUMS-ac6a00e-preflight-chain-audit",
        "em_gamma_preflight_contract_index_20260512.md",
        "em_gamma_preflight_chain_audit_20260512.md",
    ):
        require(REPORT, marker)

    for phrase in (
        "detector/event",
        "physics-parity claim",
        "speedup claim",
        "deferred-process implementation",
    ):
        require_count(REPORT, phrase, 1)

    for marker in (
        "NAME g4gpu_em_publication_audit",
        "scripts/verify_em_gamma_publication_audit.py",
        "NAME g4gpu_em_publication_artifacts",
        "scripts/verify_em_gamma_publication_artifacts.py",
    ):
        require(CMAKE, marker)

    for path in (REPORT, CMAKE, SELF):
        for forbidden in ("NN" "BAR" + "_Detector", "nnbar" + "_reconstruction"):
            require_absent(path, forbidden)

    print("EM_GAMMA_PUBLICATION_AUDIT_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
