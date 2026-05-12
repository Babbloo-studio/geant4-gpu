#!/usr/bin/env python3
"""Focused tests for optimization-registry fail-closed validation."""

from __future__ import annotations

from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmarks.harness.optimization_registry import (  # noqa: E402
    OptimizationRegistryError,
    load_registry,
    require_entry,
    validate_entry,
)


def _write_registry(tmp: Path, text: str) -> Path:
    path = tmp / "optimizations_registry.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def test_bd001_registry_row_shape_passes(tmp_path: Path) -> None:
    path = _write_registry(
        tmp_path,
        """
BD-geant4-001:
  branch: lane/bd-geant4-001-moller-bhabha-inverse-sampler
  cmake_flags: "-DG4GPU_BD001_MOLLER_BHABHA=ON"
  description: "Moller/Bhabha inverse-sampler candidate"
  depends_on: []
  claim_level: L2
  notes: "preflight only"
  optimized_geant4_prefix: "/local/slurmtmp/bd001-optimized-geant4"
  review_status: approved
  reviewed_by:
    - reviewer@example.invalid
  reviewed_commit: "0123456789abcdef0123456789abcdef01234567"
  review_artifact: "/tmp/bd001-review.txt"
""",
    )
    entry = require_entry("BD-geant4-001", path)
    assert entry.opt_id == "BD-geant4-001"
    assert entry.branch.endswith("inverse-sampler")
    assert entry.cmake_flags == "-DG4GPU_BD001_MOLLER_BHABHA=ON"
    assert entry.depends_on == ()
    assert entry.claim_level == "L2"
    assert entry.optimized_geant4_prefix == "/local/slurmtmp/bd001-optimized-geant4"
    assert entry.review_status == "approved"
    assert entry.reviewed_by == ("reviewer@example.invalid",)
    assert entry.reviewed_commit == "0123456789abcdef0123456789abcdef01234567"
    assert entry.review_artifact == "/tmp/bd001-review.txt"


def test_missing_registry_or_entry_fails_closed(tmp_path: Path) -> None:
    try:
        load_registry(tmp_path / "missing.yaml")
    except OptimizationRegistryError as exc:
        assert "optimization registry missing" in str(exc)
    else:
        raise AssertionError("missing registry was accepted")

    path = _write_registry(
        tmp_path,
        """
BD-geant4-032:
  branch: lane/bd32
  cmake_flags: ""
  description: "other optimization"
  depends_on: []
""",
    )
    try:
        require_entry("BD-geant4-001", path)
    except OptimizationRegistryError as exc:
        assert "lacks required entry" in str(exc)
    else:
        raise AssertionError("missing BD-001 registry row was accepted")


def test_invalid_registry_shapes_fail_closed() -> None:
    for raw, marker in (
        ({"branch": "lane/bd001", "description": "missing fields", "depends_on": []}, "missing required fields"),
        ({"branch": "", "cmake_flags": "", "description": "x", "depends_on": []}, "branch must be non-empty"),
        ({"branch": "lane/bd001", "cmake_flags": "", "description": "x", "depends_on": [""]}, "entries must be"),
        (
            {
                "branch": "lane/bd001",
                "cmake_flags": "",
                "description": "x",
                "depends_on": [],
                "speedup_mean": 1.2,
            },
            "unknown fields",
        ),
        (
            {
                "branch": "lane/bd001",
                "cmake_flags": "",
                "description": "x",
                "depends_on": [],
                "claim_level": "L3",
                "notes": "not paper ready",
            },
            "notes must be empty",
        ),
        (
            {
                "branch": "lane/bd001",
                "cmake_flags": "",
                "description": "x",
                "depends_on": [],
                "optimized_geant4_prefix": "relative/prefix",
            },
            "optimized_geant4_prefix must be an absolute path",
        ),
        (
            {
                "branch": "lane/bd001",
                "cmake_flags": "",
                "description": "x",
                "depends_on": [],
                "review_status": "rubber-stamped",
            },
            "review_status must be",
        ),
        (
            {
                "branch": "lane/bd001",
                "cmake_flags": "",
                "description": "x",
                "depends_on": [],
                "reviewed_by": [],
            },
            "reviewed_by must contain",
        ),
        (
            {
                "branch": "lane/bd001",
                "cmake_flags": "",
                "description": "x",
                "depends_on": [],
                "reviewed_commit": "not-a-commit",
            },
            "reviewed_commit must be",
        ),
        (
            {
                "branch": "lane/bd001",
                "cmake_flags": "",
                "description": "x",
                "depends_on": [],
                "review_artifact": "relative-review.txt",
            },
            "review_artifact must be an absolute path",
        ),
    ):
        try:
            validate_entry("BD-geant4-001", raw)
        except OptimizationRegistryError as exc:
            assert marker in str(exc)
        else:
            raise AssertionError(f"invalid registry row accepted: {raw}")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="g4gpu-registry-test-") as tmp_dir:
        tmp = Path(tmp_dir)
        test_bd001_registry_row_shape_passes(tmp)
        test_missing_registry_or_entry_fails_closed(tmp)
        test_invalid_registry_shapes_fail_closed()
    print("benchmark_harness_optimization_registry: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
