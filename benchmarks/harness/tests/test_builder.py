#!/usr/bin/env python3
"""Focused tests for benchmark-harness builder.py dry-run/build guards."""

from __future__ import annotations

import os
from pathlib import Path
import stat
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmarks.harness.builder import BuildError, build_optimized, build_vanilla, resolve_workload  # noqa: E402


def _fixture_tree(tmp: Path) -> tuple[Path, Path, Path, dict[str, str]]:
    prefix = tmp / "hibeam_env"
    (prefix / "lib/cmake/Geant4").mkdir(parents=True, exist_ok=True)
    (prefix / "lib/cmake/Geant4/Geant4Config.cmake").write_text("# fake Geant4\n", encoding="utf-8")
    geant4_source = tmp / "geant4-fork"
    (geant4_source / "examples/extended/electromagnetic/TestEm0").mkdir(parents=True, exist_ok=True)
    fake_bin = tmp / "bin"
    fake_bin.mkdir(exist_ok=True)
    fake_cmake = fake_bin / "cmake"
    fake_cmake.write_text(
        """#!/usr/bin/env python3
import os
from pathlib import Path
import sys

print("fake cmake " + " ".join(sys.argv[1:]))
mode = os.environ.get("FAKE_CMAKE_MODE", "ok")
if mode == "error":
    print("CMake Error: configured fake failure")
    raise SystemExit(0)
if len(sys.argv) > 2 and sys.argv[1] == "-S":
    build_dir = Path(sys.argv[sys.argv.index("-B") + 1])
    build_dir.mkdir(parents=True, exist_ok=True)
elif len(sys.argv) > 2 and sys.argv[1] == "--build":
    build_dir = Path(sys.argv[2])
    target = sys.argv[sys.argv.index("--target") + 1] if "--target" in sys.argv else "unknown"
    if mode != "missing_binary":
        binary = build_dir / "benchmarks" / target if target.startswith("benchmark_") else build_dir / target
        binary.parent.mkdir(parents=True, exist_ok=True)
        binary.write_text("#!/usr/bin/env bash\\nexit 0\\n", encoding="utf-8")
        binary.chmod(0o755)
""",
        encoding="utf-8",
    )
    fake_cmake.chmod(fake_cmake.stat().st_mode | stat.S_IEXEC)
    env = {"PATH": str(fake_bin) + os.pathsep + os.environ.get("PATH", "")}
    return prefix, geant4_source, fake_cmake, env


def test_build_vanilla_w1_gamma_with_fake_cmake(tmp_path: Path) -> None:
    prefix, geant4_source, fake_cmake, env = _fixture_tree(tmp_path)
    build_dir = build_vanilla(
        prefix,
        "W1",
        tmp_path / "builds",
        geant4_source=geant4_source,
        log_dir=tmp_path / "logs",
        hw_id="H3",
        cmake=fake_cmake,
        env=env,
    )
    assert build_dir.name == "vanilla_vanilla_W1"
    assert (build_dir / "benchmarks/benchmark_gamma_100mev").is_file()
    log = (tmp_path / "logs/vanilla_H3.txt").read_text(encoding="utf-8")
    assert "benchmarks/harness" not in log
    assert "sbatch" not in log
    assert "fake cmake -S" in log
    assert "-DGeant4_DIR=" in log


def test_build_optimized_dry_run_writes_plan_only(tmp_path: Path) -> None:
    prefix, geant4_source, fake_cmake, env = _fixture_tree(tmp_path)
    build_dir = build_optimized(
        prefix,
        "lane/example",
        "-DG4GPU_EXAMPLE=ON",
        "W1",
        tmp_path / "builds",
        geant4_source=geant4_source,
        log_dir=tmp_path / "logs",
        opt_id="BD-geant4-000",
        hw_id="H3",
        cmake=fake_cmake,
        dry_run=True,
        verify_ref=False,
        env=env,
    )
    assert build_dir.name == "optimized_BD-geant4-000_W1"
    assert not (build_dir / "benchmarks/benchmark_gamma_100mev").exists()
    log = (tmp_path / "logs/BD-geant4-000_H3.txt").read_text(encoding="utf-8")
    assert "DRY-RUN" in log
    assert "-DG4GPU_EXAMPLE=ON" in log
    assert "fake cmake" not in log


def test_build_log_error_is_fail_closed(tmp_path: Path) -> None:
    prefix, geant4_source, fake_cmake, env = _fixture_tree(tmp_path)
    env = {**env, "FAKE_CMAKE_MODE": "error"}
    try:
        build_vanilla(
            prefix,
            "W1",
            tmp_path / "builds",
            geant4_source=geant4_source,
            log_dir=tmp_path / "logs",
            cmake=fake_cmake,
            env=env,
        )
    except BuildError as exc:
        assert "build log contains Error" in str(exc)
    else:
        raise AssertionError("builder accepted a CMake transcript containing Error")


def test_missing_binary_is_fail_closed(tmp_path: Path) -> None:
    prefix, geant4_source, fake_cmake, env = _fixture_tree(tmp_path)
    env = {**env, "FAKE_CMAKE_MODE": "missing_binary"}
    try:
        build_vanilla(
            prefix,
            "W1",
            tmp_path / "builds",
            geant4_source=geant4_source,
            log_dir=tmp_path / "logs",
            cmake=fake_cmake,
            env=env,
        )
    except BuildError as exc:
        assert "expected benchmark binary is absent" in str(exc)
    else:
        raise AssertionError("builder accepted a build with no benchmark binary")


def test_w5_w6_are_methodology_blocked_until_true_nnbar_drivers_exist() -> None:
    for workload, expected in {
        "W5": "NNBAR full event (signal)",
        "w6": "NNBAR full event (cosmic mu)",
    }.items():
        try:
            resolve_workload(workload)
        except BuildError as exc:
            message = str(exc)
            assert "methodology-blocked" in message
            assert expected in message
            assert "stand-in event driver" in message
            assert "docs/specs/w5_w6_full_event_drivers.md" in message
        else:
            raise AssertionError(f"{workload} resolved before a true NNBAR full-event driver exists")


def test_stand_in_events_resolve_only_by_event_name_not_w5_w6() -> None:
    optical = resolve_workload("optical_scintillator")
    beam = resolve_workload("beam_neutron")
    assert optical.workload_id == "optical_scintillator"
    assert optical.target == "benchmark_optical_scintillator"
    assert beam.workload_id == "beam_neutron"
    assert beam.target == "benchmark_beam_neutron"


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        test_build_vanilla_w1_gamma_with_fake_cmake(tmp)
        test_build_optimized_dry_run_writes_plan_only(tmp)
        test_build_log_error_is_fail_closed(tmp)
        test_missing_binary_is_fail_closed(tmp)
        test_w5_w6_are_methodology_blocked_until_true_nnbar_drivers_exist()
        test_stand_in_events_resolve_only_by_event_name_not_w5_w6()
    print("benchmark_harness_builder: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
