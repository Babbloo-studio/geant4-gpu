#!/usr/bin/env python3
"""Verify BD-geant4-001 measured-result readiness remains fail-closed.

This is a static gap verifier. It does not submit SLURM jobs, run benchmark
binaries, generate Parquet files, append results, or make parity/speedup claims.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmarks.harness.bd001_branch_gate import BD001BranchGateError, bd001_branch_gate  # noqa: E402
from benchmarks.harness.bd001_review_gate import BD001ReviewGateError, bd001_review_gate  # noqa: E402
from benchmarks.harness.optimization_registry import DEFAULT_REGISTRY, require_entry  # noqa: E402
from benchmarks.harness.sampler_observables import BD001_REQUIRED_OBSERVABLES  # noqa: E402

SOURCE_REPO = Path("/projects/hep/fs10/shared/nnbar/billy/geant4-fork")
REPORT = ROOT / "docs/reports/bd_geant4_001_result_readiness_20260513.md"
RESULTS_PARQUET = ROOT / "benchmarks/results/results.parquet"
SAMPLER_VALIDATION_DIR = ROOT / "benchmarks/validation/bd001_sampler"
EXPECTED_SAMPLER_PARQUETS = (
    SAMPLER_VALIDATION_DIR / "vanilla_sampler_observables.parquet",
    SAMPLER_VALIDATION_DIR / "optimized_sampler_observables.parquet",
)
REQUIRED_REPORT_MARKERS = (
    "BD-geant4-001 measured-result readiness",
    "OPEN: approved_review_artifact_missing_or_blocked",
    "OPEN: optimized_prefix_config_missing",
    "OPEN: sampler_validation_parquets_missing",
    "OPEN: canonical_results_parquet_missing",
    "BD001_RESULT_READINESS_BLOCKED_OK",
    "No SLURM",
)


def _require_text(path: Path, markers: tuple[str, ...]) -> None:
    if not path.is_file():
        raise AssertionError(f"missing required file: {path.relative_to(ROOT)}")
    text = path.read_text(encoding="utf-8")
    missing = [marker for marker in markers if marker not in text]
    if missing:
        raise AssertionError(f"{path.relative_to(ROOT)} missing markers: {missing}")


def _expect_error(call, exc_type: type[Exception], marker: str) -> str:
    try:
        call()
    except exc_type as exc:
        message = str(exc)
        if marker not in message:
            raise AssertionError(f"expected {marker!r}, got {message!r}") from exc
        return message
    raise AssertionError(f"expected {exc_type.__name__} containing {marker!r}")


def _require_sampler_parquets_missing() -> list[str]:
    existing = [path for path in EXPECTED_SAMPLER_PARQUETS if path.exists()]
    if existing:
        raise AssertionError(
            "staged BD001 sampler-validation Parquets require replacing this blocker verifier: "
            + ", ".join(str(path.relative_to(ROOT)) for path in existing)
        )
    return [str(path.relative_to(ROOT)) for path in EXPECTED_SAMPLER_PARQUETS]


def main() -> int:
    entry = require_entry("BD-geant4-001", DEFAULT_REGISTRY)
    if entry.review_status != "blocked":
        raise AssertionError("BD001 default registry row must remain blocked until measured-result approval")

    review_error = _expect_error(
        lambda: bd001_review_gate(DEFAULT_REGISTRY, source_repo=SOURCE_REPO),
        BD001ReviewGateError,
        "review_status must be 'approved'",
    )
    print("BD001_RESULT_READINESS_APPROVED_REVIEW_BLOCKED_OK")

    prefix_error = _expect_error(
        lambda: bd001_branch_gate(DEFAULT_REGISTRY, source_repo=SOURCE_REPO, require_prefix_config=True),
        BD001BranchGateError,
        "missing Geant4Config.cmake under optimized prefix",
    )
    print("BD001_RESULT_READINESS_OPTIMIZED_PREFIX_BLOCKED_OK")

    missing_parquets = _require_sampler_parquets_missing()
    if set(BD001_REQUIRED_OBSERVABLES) != {
        "sampler_x", "delta_ray_ke_mev", "delta_ray_theta_rad", "downstream_dedx_mev_mm"
    }:
        raise AssertionError(f"unexpected BD001 sampler observable contract: {BD001_REQUIRED_OBSERVABLES}")
    print("BD001_RESULT_READINESS_SAMPLER_PARQUETS_BLOCKED_OK")

    if RESULTS_PARQUET.exists():
        raise AssertionError("canonical results.parquet exists; replace this blocker before result promotion")
    print("BD001_RESULT_READINESS_RESULTS_ROW_BLOCKED_OK")

    _require_text(REPORT, REQUIRED_REPORT_MARKERS)
    print("BD001_RESULT_READINESS_REPORT_OK")
    print("BD001_RESULT_READINESS_BLOCKED_OK")
    print("BD001_RESULT_READINESS_GAPS review={!r} prefix={!r} sampler_parquets={}".format(
        review_error, prefix_error, ",".join(missing_parquets)
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
