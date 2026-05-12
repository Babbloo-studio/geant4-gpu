#!/usr/bin/env python3
"""Verify every EM/gamma report has an explicit verifier coverage class."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "docs/reports"
CMAKE = ROOT / "CMakeLists.txt"
COVERAGE_REPORT = REPORT_DIR / "em_gamma_report_coverage_20260512.md"
SELF = Path(__file__)


@dataclass(frozen=True)
class Coverage:
    script: str
    ctest: str | None
    reason: str


EXPECTED = {
    "em_gamma_bremsstrahlung_contract_20260512.md": Coverage(
        "scripts/verify_em_gamma_bremsstrahlung_contract.py",
        "g4gpu_em_bremsstrahlung_contract",
        "per-process contract",
    ),
    "em_gamma_ctest_execution_boundary_20260512.md": Coverage(
        "scripts/verify_em_gamma_ctest_execution_boundary.py",
        "g4gpu_em_ctest_execution_boundary",
        "CTest command boundary",
    ),
    "em_gamma_claim_boundary_20260512.md": Coverage(
        "scripts/verify_em_gamma_claim_boundary.py",
        "g4gpu_em_claim_boundary",
        "premature claim boundary",
    ),
    "em_gamma_current_publication_audit_20260512.md": Coverage(
        "scripts/verify_em_gamma_publication_audit.py",
        "g4gpu_em_publication_audit",
        "current publication audit",
    ),
    "em_gamma_deferred_contract_index_20260512.md": Coverage(
        "scripts/verify_em_gamma_deferred_contract_index.py",
        "g4gpu_em_deferred_contract_index",
        "deferred contract index",
    ),
    "em_gamma_deferred_process_gap_audit_20260512.md": Coverage(
        "scripts/verify_em_gamma_deferred_process_gap.py",
        "g4gpu_em_deferred_process_gap",
        "deferred process gap",
    ),
    "em_gamma_implementation_roadmap_20260512.md": Coverage(
        "scripts/verify_em_gamma_implementation_roadmap.py",
        "g4gpu_em_implementation_roadmap",
        "implementation roadmap",
    ),
    "em_gamma_kernel_completion_audit_20260512.md": Coverage(
        "scripts/verify_em_gamma_static_contract.py",
        "g4gpu_em_static_contract",
        "shared original-scaffold static contract",
    ),
    "em_gamma_lane_objective_audit_20260512.md": Coverage(
        "scripts/verify_em_gamma_lane_objective_audit.py",
        "g4gpu_em_lane_objective_audit",
        "lane prompt-to-artifact objective audit",
    ),
    "em_gamma_line_cap_guard_20260512.md": Coverage(
        "scripts/verify_em_gamma_line_caps.py",
        "g4gpu_em_line_caps",
        "compact artifact line-cap guard",
    ),
    "em_gamma_pair_contract_20260512.md": Coverage(
        "scripts/verify_em_gamma_pair_contract.py",
        "g4gpu_em_pair_contract",
        "per-process contract",
    ),
    "em_gamma_option_boundary_20260512.md": Coverage(
        "scripts/verify_em_gamma_option_boundary.py",
        "g4gpu_em_option_boundary",
        "CMake option boundary",
    ),
    "em_gamma_option_off_config_20260512.md": Coverage(
        "scripts/verify_em_gamma_option_off_config.py",
        "g4gpu_em_option_off_config",
        "CMake option-OFF configure gate",
    ),
    "em_gamma_photoelectric_contract_20260512.md": Coverage(
        "scripts/verify_em_gamma_photoelectric_contract.py",
        "g4gpu_em_photoelectric_contract",
        "per-process contract",
    ),
    "em_gamma_preflight_chain_audit_20260512.md": Coverage(
        "scripts/verify_em_gamma_preflight_chain_audit.py",
        "g4gpu_em_preflight_chain_audit",
        "preflight chain audit",
    ),
    "em_gamma_preflight_contract_index_20260512.md": Coverage(
        "scripts/verify_em_gamma_preflight_contract_index.py",
        "g4gpu_em_preflight_contract_index",
        "preflight index",
    ),
    "em_gamma_publication_artifacts_20260512.md": Coverage(
        "scripts/verify_em_gamma_publication_artifacts.py",
        "g4gpu_em_publication_artifacts",
        "current-head fallback publication artifacts",
    ),
    "em_gamma_publication_transcript_20260512.md": Coverage(
        "scripts/verify_em_gamma_publication_transcript.py",
        "g4gpu_em_publication_transcript",
        "current-head checker transcript evidence",
    ),
    "em_gamma_publication_patch_id_20260512.md": Coverage(
        "scripts/verify_em_gamma_publication_patch_id.py",
        "g4gpu_em_publication_patch_id",
        "current-head patch content identity",
    ),
    "em_gamma_process_selector_preflight_20260512.md": Coverage(
        "scripts/verify_em_gamma_process_selector_preflight.py",
        "g4gpu_em_process_selector_preflight",
        "shared preflight contract",
    ),
    "em_gamma_report_coverage_20260512.md": Coverage(
        "scripts/verify_em_gamma_report_coverage.py",
        "g4gpu_em_report_coverage",
        "coverage inventory self-check",
    ),
    "em_gamma_rng_stream_preflight_20260512.md": Coverage(
        "scripts/verify_em_gamma_rng_stream_preflight.py",
        "g4gpu_em_rng_stream_preflight",
        "shared preflight contract",
    ),
    "em_gamma_runtime_gate_20260512.md": Coverage(
        "scripts/verify_em_gamma_runtime_gate.py",
        None,
        "manual fail-closed GPU allocation gate",
    ),
    "em_gamma_runtime_gate_gpu_20260512.md": Coverage(
        "scripts/verify_em_gamma_runtime_gpu_report.py",
        "g4gpu_em_runtime_gpu_report",
        "archived GPU runtime evidence",
    ),
    "em_gamma_secondary_buffer_preflight_20260512.md": Coverage(
        "scripts/verify_em_gamma_secondary_buffer_preflight.py",
        "g4gpu_em_secondary_buffer_preflight",
        "shared preflight contract",
    ),
    "em_gamma_source_boundary_20260512.md": Coverage(
        "scripts/verify_em_gamma_source_boundary.py",
        "g4gpu_em_source_boundary",
        "source isolation boundary",
    ),
    "em_gamma_status_code_preflight_20260512.md": Coverage(
        "scripts/verify_em_gamma_status_code_preflight.py",
        "g4gpu_em_status_code_preflight",
        "shared preflight contract",
    ),
    "em_gamma_table_owner_preflight_20260512.md": Coverage(
        "scripts/verify_em_gamma_table_owner_preflight.py",
        "g4gpu_em_table_owner_preflight",
        "shared preflight contract",
    ),
    "em_gamma_validation_fixture_contract_20260512.md": Coverage(
        "scripts/verify_em_gamma_validation_fixture_contract.py",
        "g4gpu_em_validation_fixture_contract",
        "validation fixture contract",
    ),
    "em_gamma_verifier_script_boundary_20260512.md": Coverage(
        "scripts/verify_em_gamma_verifier_script_boundary.py",
        "g4gpu_em_verifier_script_boundary",
        "verifier script read-only boundary",
    ),
}


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


def main() -> int:
    actual_reports = {path.name for path in REPORT_DIR.glob("em_gamma_*_20260512.md")}
    expected_reports = set(EXPECTED)
    if actual_reports != expected_reports:
        missing = sorted(expected_reports - actual_reports)
        extra = sorted(actual_reports - expected_reports)
        raise SystemExit(f"unexpected EM/gamma report set; missing={missing} extra={extra}")

    cmake = text(CMAKE)
    for report, coverage in EXPECTED.items():
        report_path = REPORT_DIR / report
        require(report_path, "# EM/gamma")
        script_path = ROOT / coverage.script
        if not script_path.exists():
            raise SystemExit(f"missing coverage script for {report}: {coverage.script}")
        if coverage.ctest is None:
            if coverage.script in cmake:
                raise SystemExit(f"manual gate {coverage.script} must not be registered as normal CTest")
        else:
            for marker in (f"NAME {coverage.ctest}", coverage.script):
                if marker not in cmake:
                    raise SystemExit(f"missing CTest marker for {report}: {marker}")

    for marker in (
        "Every `docs/reports/em_gamma_*_20260512.md` markdown report",
        "Manual fail-closed gate",
        "strict runtime gate script remains manual/fail-closed",
        "does not authorize\nSLURM submission",
    ):
        require(COVERAGE_REPORT, marker)

    for path in (COVERAGE_REPORT, SELF):
        for forbidden in ("NN" "BAR" + "_Detector", "nnbar" + "_reconstruction"):
            require_absent(path, forbidden)

    print("EM_GAMMA_REPORT_COVERAGE_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
