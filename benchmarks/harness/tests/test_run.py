#!/usr/bin/env python3
"""Focused tests for benchmark-harness run.py CLI wiring."""

from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import io
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmarks.harness.run import main as run_main  # noqa: E402


def test_module_help_exits_zero() -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "benchmarks.harness.run", "--help"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout
    assert "--generate-reference" in proc.stdout
    assert "--collect" in proc.stdout


def test_dry_run_w1_pl1_h3_prints_sbatch_without_side_effects(tmp_path: Path) -> None:
    output = io.StringIO()
    with redirect_stdout(output):
        rc = run_main(
            [
                "--opt-id",
                "BD-geant4-032",
                "--opt-branch",
                "lane/bd-geant4-032",
                "--workload",
                "W1",
                "--physics-list",
                "PL1",
                "--hw",
                "H3",
                "--n-seeds",
                "2",
                "--n-events",
                "5",
                "--repo-root",
                str(tmp_path / "repo"),
                "--geant4-prefix",
                str(tmp_path / "hibeam_env"),
                "--python",
                sys.executable,
            ]
        )
    text = output.getvalue()
    assert rc == 0
    assert text.startswith("#!/usr/bin/env bash")
    assert "#SBATCH --job-name=g4gpu-BD-geant4-032-W1" in text
    assert "WORKLOAD_ID=W1" in text
    assert "PHYSICS_LIST=PL1" in text
    assert "HW_ID=H3" in text
    assert "SEEDS=(1001 1002)" in text
    assert "sbatch" not in text.lower().splitlines()[0]
    assert not (tmp_path / "repo/benchmarks/raw/BD-geant4-032").exists()


def test_submit_dry_run_writes_valid_scripts_but_does_not_call_sbatch(tmp_path: Path) -> None:
    script_dir = tmp_path / "scripts"
    output = io.StringIO()
    with redirect_stdout(output):
        rc = run_main(
            [
                "--opt-id",
                "phase3-rtx",
                "--opt-branch",
                "lane/g4gpu-phase3",
                "--workload",
                "W1",
                "--physics-list",
                "PL1",
                "--hw",
                "H3",
                "--seed",
                "42",
                "--repo-root",
                str(tmp_path / "repo"),
                "--script-dir",
                str(script_dir),
                "--submit",
                "--dry-run",
                "--sbatch",
                str(tmp_path / "missing-sbatch"),
            ]
        )
    assert rc == 0
    scripts = list(script_dir.glob("*.sbatch"))
    assert len(scripts) == 1
    assert "Submitted batch job" not in output.getvalue()
    proc = subprocess.run(["bash", "-n", str(scripts[0])], check=False)
    assert proc.returncode == 0


def test_collect_stub_fails_closed_unless_dry_run() -> None:
    err = io.StringIO()
    with redirect_stderr(err):
        rc = run_main(["--collect", "--opt-id", "x", "--workload", "W1", "--physics-list", "PL1", "--hw", "H3"])
    assert rc == 2
    assert "COLLECT_NOT_IMPLEMENTED" in err.getvalue()
    output = io.StringIO()
    with redirect_stdout(output):
        dry_rc = run_main(["--collect", "--dry-run"])
    assert dry_rc == 0
    assert "COLLECT_STUB" in output.getvalue()


def test_generate_reference_is_dry_run_stub(tmp_path: Path) -> None:
    output = io.StringIO()
    with redirect_stdout(output):
        rc = run_main(
            [
                "--opt-id",
                "vanilla",
                "--workload",
                "W1",
                "--physics-list",
                "PL1",
                "--hw",
                "H3",
                "--n-seeds",
                "1",
                "--repo-root",
                str(tmp_path / "repo"),
                "--generate-reference",
            ]
        )
    text = output.getvalue()
    assert rc == 0
    assert "REFERENCE_GENERATION_STUB" in text
    assert "benchmarks/reference/W1/PL1" in text


def test_generate_reference_submit_is_blocked(tmp_path: Path) -> None:
    err = io.StringIO()
    with redirect_stderr(err):
        rc = run_main(
            [
                "--opt-id",
                "vanilla",
                "--workload",
                "W1",
                "--physics-list",
                "PL1",
                "--hw",
                "H3",
                "--repo-root",
                str(tmp_path / "repo"),
                "--generate-reference",
                "--submit",
            ]
        )
    assert rc == 2
    assert "deferred to task 7" in err.getvalue()


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        test_module_help_exits_zero()
        test_dry_run_w1_pl1_h3_prints_sbatch_without_side_effects(tmp)
        test_submit_dry_run_writes_valid_scripts_but_does_not_call_sbatch(tmp)
        test_collect_stub_fails_closed_unless_dry_run()
        test_generate_reference_is_dry_run_stub(tmp)
        test_generate_reference_submit_is_blocked(tmp)
    print("benchmark_harness_run: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
