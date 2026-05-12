#!/usr/bin/env python3
"""Verify BD-geant4-001 guarded-smoke readiness remains fail-closed.

This is a static prerequisite gate. It does not configure/build Geant4, submit
SLURM, run benchmark events, regenerate references, append result rows, or make
parity/speedup claims.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmarks.harness.bd001_branch_gate import BD001BranchGateError, bd001_branch_gate  # noqa: E402
from benchmarks.harness.bd001_review_gate import BD001ReviewGateError, bd001_review_gate  # noqa: E402
from benchmarks.harness.bd001_smoke_contract import REQUIRED_NO_PROMOTION_CHECKS  # noqa: E402
from benchmarks.harness.optimization_registry import DEFAULT_REGISTRY, require_entry  # noqa: E402
from benchmarks.harness.sampler_observables import BD001_REQUIRED_OBSERVABLES  # noqa: E402

SOURCE_REPO = Path("/projects/hep/fs10/shared/nnbar/billy/geant4-fork")
REPORT = ROOT / "docs/reports/bd_geant4_001_smoke_readiness_20260512.md"
CMAKE = ROOT / "CMakeLists.txt"
REVIEW_GATE = ROOT / "benchmarks/harness/bd001_review_gate.py"
BRANCH_GATE = ROOT / "benchmarks/harness/bd001_branch_gate.py"
REGISTRY = ROOT / "benchmarks/harness/optimization_registry.py"
RESULT_ROW = ROOT / "benchmarks/results/results.parquet"
REQUIRED_OBSERVABLES = {
    "sampler_x",
    "delta_ray_ke_mev",
    "delta_ray_theta_rad",
    "downstream_dedx_mev_mm",
}
REQUIRED_NO_PROMOTION = {
    "result_tag_not_speedup",
    "claim_level_not_paper",
    "manual_promotion_required",
    "dry_run_no_results_append",
}


def require_text(path: Path, marker: str) -> None:
    if not path.is_file():
        raise AssertionError(f"missing required file: {path.relative_to(ROOT)}")
    if marker not in path.read_text(encoding="utf-8"):
        raise AssertionError(f"missing marker in {path.relative_to(ROOT)}: {marker}")


def expect_error(call, exc_type: type[Exception], marker: str) -> None:
    try:
        call()
    except exc_type as exc:
        if marker not in str(exc):
            raise AssertionError(f"expected error containing {marker!r}, got {exc!r}") from exc
    else:
        raise AssertionError(f"expected {exc_type.__name__} containing {marker!r}")


def main() -> int:
    entry = require_entry("BD-geant4-001", DEFAULT_REGISTRY)
    if entry.review_status != "blocked":
        raise AssertionError("BD001 default registry row must stay review_status: blocked")
    for marker in (
        "no approved review",
        "optimized install prefix",
        "sampler validation",
        "smoke",
    ):
        if marker not in entry.notes:
            raise AssertionError(f"BD001 blocked registry notes missing {marker!r}")

    expect_error(
        lambda: bd001_review_gate(DEFAULT_REGISTRY, source_repo=SOURCE_REPO),
        BD001ReviewGateError,
        "review_status must be 'approved'",
    )
    for path, markers in {
        REVIEW_GATE: (
            "review_artifact_sha256",
            "BD001_SOURCE_COMMIT",
            "BD001_HANDOFF_COMMIT",
            "PLACEHOLDER_OR_NEGATED_REVIEW_TOKENS",
        ),
        BRANCH_GATE: ("source/processes/electromagnetic/standard/src/G4MollerBhabhaModel.cc", "BD001_FALLBACK_TOKEN"),
        REGISTRY: ("review_artifact_sha256", "64-character sha256"),
    }.items():
        for marker in markers:
            require_text(path, marker)
    print("BD001_APPROVED_REVIEW_ARTIFACT_BLOCKED_OK")
    print("BD001_APPROVED_REVIEW_ARTIFACT_GATE_OK")

    expect_error(
        lambda: bd001_branch_gate(DEFAULT_REGISTRY, source_repo=SOURCE_REPO, require_prefix_config=True),
        BD001BranchGateError,
        "missing Geant4Config.cmake under optimized prefix",
    )
    print("BD001_OPTIMIZED_PREFIX_BLOCKED_OK")

    if set(BD001_REQUIRED_OBSERVABLES) != REQUIRED_OBSERVABLES:
        raise AssertionError(f"unexpected sampler-observable contract: {BD001_REQUIRED_OBSERVABLES}")
    print("BD001_SAMPLER_VALIDATION_CONTRACT_OK")

    if set(REQUIRED_NO_PROMOTION_CHECKS) != REQUIRED_NO_PROMOTION:
        raise AssertionError(f"unexpected guarded-smoke no-promotion checks: {REQUIRED_NO_PROMOTION_CHECKS}")
    if RESULT_ROW.exists():
        raise AssertionError("BD001 readiness gate must not coexist with canonical results.parquet")
    print("BD001_GUARDED_SMOKE_RESULT_ROW_BLOCKED_OK")

    for marker in (
        "g4gpu_benchmark_harness_bd001_review_gate",
        "g4gpu_benchmark_harness_sampler_observables",
        "g4gpu_benchmark_harness_bd001_smoke_contract",
        "g4gpu_bd001_smoke_readiness",
        "scripts/verify_bd001_smoke_readiness.py",
    ):
        require_text(CMAKE, marker)

    for path, markers in {
        ROOT / "docs/reports/bd_geant4_001_review_registry_handoff_blocker_20260512.md": (
            "No approved review artifact",
            "Optimized Geant4 install prefix",
            "Sampler-observable validation Parquets",
        ),
        ROOT / "docs/reports/bd_geant4_001_guarded_smoke_contract_20260512.md": (
            "non-promotional `result_tag`",
            "no-promotion checks",
        ),
        ROOT / "docs/reports/bd_geant4_001_sampler_observables_preflight_20260512.md": (
            "sampled `x`",
            "delta_ray_ke_mev",
            "delta_ray_theta_rad",
            "downstream_dedx_mev_mm",
        ),
        REPORT: (
            "approved review artifact",
            "optimized Geant4 prefix",
            "sampler validation",
            "guarded smoke/result-row",
            "No SLURM",
            "BD001_SMOKE_READINESS_BLOCKED_OK",
        ),
    }.items():
        for marker in markers:
            require_text(path, marker)

    print("BD001_SMOKE_READINESS_REPORT_OK")
    print("BD001_SMOKE_READINESS_BLOCKED_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
