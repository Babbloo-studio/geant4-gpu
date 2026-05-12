#!/usr/bin/env python3
"""Verify the EM/gamma CTest commands stay local and non-production shaped."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CMAKE = ROOT / "CMakeLists.txt"
REPORT = ROOT / "docs/reports/em_gamma_ctest_execution_boundary_20260512.md"
SELF = Path(__file__)

EXPECTED_SCRIPT_TESTS = {
    "g4gpu_em_deferred_process_gap": "scripts/verify_em_gamma_deferred_process_gap.py",
    "g4gpu_em_static_contract": "scripts/verify_em_gamma_static_contract.py",
    "g4gpu_em_stub_fail_closed": "scripts/verify_em_gamma_stub_fail_closed.py",
    "g4gpu_em_publication_audit": "scripts/verify_em_gamma_publication_audit.py",
    "g4gpu_em_publication_artifacts": "scripts/verify_em_gamma_publication_artifacts.py",
    "g4gpu_em_publication_transcript": "scripts/verify_em_gamma_publication_transcript.py",
    "g4gpu_em_publication_patch_id": "scripts/verify_em_gamma_publication_patch_id.py",
    "g4gpu_em_source_boundary": "scripts/verify_em_gamma_source_boundary.py",
    "g4gpu_em_ctest_execution_boundary": "scripts/verify_em_gamma_ctest_execution_boundary.py",
    "g4gpu_em_report_coverage": "scripts/verify_em_gamma_report_coverage.py",
    "g4gpu_em_lane_objective_audit": "scripts/verify_em_gamma_lane_objective_audit.py",
    "g4gpu_em_claim_boundary": "scripts/verify_em_gamma_claim_boundary.py",
    "g4gpu_em_verifier_script_boundary": "scripts/verify_em_gamma_verifier_script_boundary.py",
    "g4gpu_em_runtime_sbatch_contract": "scripts/verify_em_gamma_runtime_sbatch.py",
    "g4gpu_em_runtime_gpu_report": "scripts/verify_em_gamma_runtime_gpu_report.py",
    "g4gpu_em_photoelectric_contract": "scripts/verify_em_gamma_photoelectric_contract.py",
    "g4gpu_em_pair_contract": "scripts/verify_em_gamma_pair_contract.py",
    "g4gpu_em_bremsstrahlung_contract": "scripts/verify_em_gamma_bremsstrahlung_contract.py",
    "g4gpu_em_deferred_contract_index": "scripts/verify_em_gamma_deferred_contract_index.py",
    "g4gpu_em_implementation_roadmap": "scripts/verify_em_gamma_implementation_roadmap.py",
    "g4gpu_em_validation_fixture_contract": "scripts/verify_em_gamma_validation_fixture_contract.py",
    "g4gpu_em_table_owner_preflight": "scripts/verify_em_gamma_table_owner_preflight.py",
    "g4gpu_em_secondary_buffer_preflight": "scripts/verify_em_gamma_secondary_buffer_preflight.py",
    "g4gpu_em_rng_stream_preflight": "scripts/verify_em_gamma_rng_stream_preflight.py",
    "g4gpu_em_process_selector_preflight": "scripts/verify_em_gamma_process_selector_preflight.py",
    "g4gpu_em_status_code_preflight": "scripts/verify_em_gamma_status_code_preflight.py",
    "g4gpu_em_preflight_contract_index": "scripts/verify_em_gamma_preflight_contract_index.py",
    "g4gpu_em_preflight_chain_audit": "scripts/verify_em_gamma_preflight_chain_audit.py",
    "g4gpu_em_option_boundary": "scripts/verify_em_gamma_option_boundary.py",
    "g4gpu_em_option_off_config": "scripts/verify_em_gamma_option_off_config.py",
    "g4gpu_em_line_caps": "scripts/verify_em_gamma_line_caps.py",
}

ALLOWED_TESTS = set(EXPECTED_SCRIPT_TESTS) | {"g4gpu_em_klein_nishina"}
FORBIDDEN_COMMAND_MARKERS = (
    "benchmark_",
    "benchmarks/",
    "write_parquet.py",
    "--output",
    "Particle_output",
    "results.parquet",
    "${CMAKE_BINARY_DIR}/benchmarks",
    "scripts/verify_em_gamma_runtime_gate.py",
    "COMMAND sbatch",
    "COMMAND srun",
    "COMMAND ${SBATCH",
    "COMMAND ${SRUN",
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


def ctest_blocks(cmake_text: str) -> dict[str, str]:
    pattern = re.compile(r"add_test\(\s*NAME\s+(g4gpu_em_[A-Za-z0-9_]+)(.*?)\)", re.S)
    return {match.group(1): match.group(0) for match in pattern.finditer(cmake_text)}


def main() -> int:
    body = text(CMAKE)
    blocks = ctest_blocks(body)
    found = set(blocks)
    if found != ALLOWED_TESTS:
        missing = sorted(ALLOWED_TESTS - found)
        extra = sorted(found - ALLOWED_TESTS)
        raise SystemExit(f"unexpected EM CTest set; missing={missing} extra={extra}")

    kn_block = blocks["g4gpu_em_klein_nishina"]
    if "${CMAKE_BINARY_DIR}/tests/test_em_klein_nishina" not in kn_block:
        raise SystemExit("g4gpu_em_klein_nishina no longer points at the standalone test binary")
    require(CMAKE, "set_tests_properties(g4gpu_em_klein_nishina PROPERTIES SKIP_RETURN_CODE 77)")

    for name, script in EXPECTED_SCRIPT_TESTS.items():
        block = blocks[name]
        if "${Python3_EXECUTABLE}" not in block:
            raise SystemExit(f"{name} is not a Python verifier CTest target")
        if script not in block:
            raise SystemExit(f"{name} does not execute expected verifier {script}")

    for name, block in blocks.items():
        for marker in FORBIDDEN_COMMAND_MARKERS:
            if marker in block:
                raise SystemExit(f"forbidden production-shaped marker {marker!r} in {name}")
        for forbidden in ("NN" "BAR" + "_Detector", "nnbar" + "_reconstruction"):
            if forbidden in block:
                raise SystemExit(f"forbidden isolation marker in CTest command for {name}")

    for marker in (
        "fail-closed documentation and verifier artifact only",
        "Every other `g4gpu_em_*` CTest target executes `${Python3_EXECUTABLE}`",
        "must not call benchmark executables",
        "must not\nsubmit the wrapper",
        "No detector/event workload, benchmark result row, physics-parity claim",
        "does not authorize SLURM submission",
    ):
        require(REPORT, marker)

    for path in (REPORT, SELF):
        for forbidden in ("NN" "BAR" + "_Detector", "nnbar" + "_reconstruction"):
            require_absent(path, forbidden)

    print("EM_GAMMA_CTEST_EXECUTION_BOUNDARY_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
