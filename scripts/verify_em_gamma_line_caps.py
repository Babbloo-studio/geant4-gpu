#!/usr/bin/env python3
"""Verify EM/gamma scaffold and verifier artifacts stay compact."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs/reports/em_gamma_line_cap_guard_20260512.md"
SELF = Path(__file__)
LIMIT = 500

PATHS = (
    "CMakeLists.txt",
    "include/g4gpu/EMStepKernel.hh",
    "src/physics/EMStepKernel.cu",
    "tests/test_em_klein_nishina.cu",
    "slurm/em_gamma_runtime_gate.sbatch",
    "scripts/verify_em_gamma_bremsstrahlung_contract.py",
    "scripts/verify_em_gamma_claim_boundary.py",
    "scripts/verify_em_gamma_ctest_execution_boundary.py",
    "scripts/verify_em_gamma_deferred_contract_index.py",
    "scripts/verify_em_gamma_deferred_process_gap.py",
    "scripts/verify_em_gamma_implementation_roadmap.py",
    "scripts/verify_em_gamma_lane_objective_audit.py",
    "scripts/verify_em_gamma_line_caps.py",
    "scripts/verify_em_gamma_option_boundary.py",
    "scripts/verify_em_gamma_option_off_config.py",
    "scripts/verify_em_gamma_pair_contract.py",
    "scripts/verify_em_gamma_photoelectric_contract.py",
    "scripts/verify_em_gamma_preflight_chain_audit.py",
    "scripts/verify_em_gamma_preflight_contract_index.py",
    "scripts/verify_em_gamma_process_selector_preflight.py",
    "scripts/verify_em_gamma_publication_artifacts.py",
    "scripts/verify_em_gamma_publication_audit.py",
    "scripts/verify_em_gamma_publication_patch_id.py",
    "scripts/verify_em_gamma_publication_transcript.py",
    "scripts/verify_em_gamma_report_coverage.py",
    "scripts/verify_em_gamma_rng_stream_preflight.py",
    "scripts/verify_em_gamma_runtime_gate.py",
    "scripts/verify_em_gamma_runtime_gpu_report.py",
    "scripts/verify_em_gamma_runtime_sbatch.py",
    "scripts/verify_em_gamma_secondary_buffer_preflight.py",
    "scripts/verify_em_gamma_source_boundary.py",
    "scripts/verify_em_gamma_static_contract.py",
    "scripts/verify_em_gamma_status_code_preflight.py",
    "scripts/verify_em_gamma_stub_fail_closed.py",
    "scripts/verify_em_gamma_table_owner_preflight.py",
    "scripts/verify_em_gamma_validation_fixture_contract.py",
    "scripts/verify_em_gamma_verifier_script_boundary.py",
)


def text(path: Path) -> str:
    if not path.exists():
        raise SystemExit(f"missing required file: {path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8", errors="replace")


def line_count(path: Path) -> int:
    return len(text(path).splitlines())


def require(path: Path, needle: str) -> None:
    if needle not in text(path):
        raise SystemExit(f"missing marker in {path.relative_to(ROOT)}: {needle}")


def require_absent(path: Path, needle: str) -> None:
    if needle in text(path):
        raise SystemExit(f"unexpected marker in {path.relative_to(ROOT)}: {needle}")


def main() -> int:
    over_limit: list[str] = []
    missing_from_guard: list[str] = []
    self_body = text(SELF)
    for rel in PATHS:
        path = ROOT / rel
        lines = line_count(path)
        if lines > LIMIT:
            over_limit.append(f"{rel}: {lines}")
        if rel != "scripts/verify_em_gamma_line_caps.py" and rel not in self_body:
            missing_from_guard.append(rel)
    if over_limit:
        raise SystemExit("EM/gamma compact-file cap exceeded: " + "; ".join(over_limit))
    if missing_from_guard:
        raise SystemExit("line-cap guard lost tracked paths: " + "; ".join(missing_from_guard))

    for marker in (
        "≤500-line cap",
        "CMakeLists.txt",
        "src/physics/EMStepKernel.cu",
        "scripts/verify_em_gamma_report_coverage.py",
        "No SLURM submission",
        "no speedup, parity, or readiness claim",
    ):
        require(REPORT, marker)

    for path in (REPORT, SELF):
        for forbidden in ("NN" "BAR" + "_Detector", "nnbar" + "_reconstruction"):
            require_absent(path, forbidden)

    print("EM_GAMMA_LINE_CAPS_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
