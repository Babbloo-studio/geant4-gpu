#!/usr/bin/env python3
"""Focused tests for benchmark-harness run.py CLI wiring and collection."""

from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import io
from pathlib import Path
import subprocess
import sys
import tempfile

import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmarks.harness.run import main as run_main  # noqa: E402
from benchmarks.harness.schema import read_rows  # noqa: E402
from benchmarks.harness.tests.test_run_bd001_registry import run_bd001_registry_selftest  # noqa: E402


def _raw_table(wall_ns: int, *, rows: int = 24, event_name: str = "gamma_100mev") -> pa.Table:
    return pa.Table.from_pydict(
        {
            "event_name": [event_name for _ in range(rows)],
            "total_deposited_energy_mev": [10.0 + 0.1 * i for i in range(rows)],
            "step_count": [100 + (i % 5) for i in range(rows)],
            "particle_multiplicity": [3 + (i % 3) for i in range(rows)],
            "first_step_length_mm": [0.5 + 0.01 * i for i in range(rows)],
            "total_wall_time_ns": [wall_ns for _ in range(rows)],
            "per_step_time_ns": [float(wall_ns) / 100.0 for _ in range(rows)],
        }
    )


def _write_raw_pair(raw_dir: Path, seed: int) -> None:
    raw_dir.mkdir(parents=True, exist_ok=True)
    pq.write_table(_raw_table(2_000_000_000), raw_dir / f"vanilla_seed_{seed}.parquet")
    pq.write_table(_raw_table(1_000_000_000), raw_dir / f"optimized_seed_{seed}.parquet")




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
    assert "--require-registry" in proc.stdout
    assert "--optimized-geant4-prefix" in proc.stdout


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
    assert "benchmark_gamma_100mev" in text
    assert "COLLECTOR_NOT_IMPLEMENTED" not in text
    assert "SEEDS=(1001 1002)" in text
    assert not (tmp_path / "repo/benchmarks/raw/BD-geant4-032").exists()



def test_w5_w6_reference_dry_run_fail_closed_until_methodology_drivers_exist(tmp_path: Path) -> None:
    for workload, expected in {
        "W5": "NNBAR full event (signal)",
        "W6": "NNBAR full event (cosmic mu)",
    }.items():
        output = io.StringIO()
        err = io.StringIO()
        with redirect_stdout(output), redirect_stderr(err):
            rc = run_main(
                [
                    "--opt-id",
                    "vanilla",
                    "--workload",
                    workload,
                    "--physics-list",
                    "PL1",
                    "--hw",
                    "H1",
                    "--n-seeds",
                    "1",
                    "--repo-root",
                    str(tmp_path / "repo"),
                    "--generate-reference",
                ]
            )
        assert rc == 2
        assert "#SBATCH" not in output.getvalue()
        assert "methodology-blocked" in err.getvalue()
        assert expected in err.getvalue()
        assert "docs/specs/w5_w6_full_event_drivers.md" in err.getvalue()


def test_stand_in_reference_dry_run_uses_event_names_not_methodology_ids(tmp_path: Path) -> None:
    output = io.StringIO()
    with redirect_stdout(output):
        rc = run_main(
            [
                "--opt-id",
                "vanilla",
                "--workload",
                "optical_scintillator",
                "beam_neutron",
                "--physics-list",
                "PL1",
                "--hw",
                "H1",
                "--n-seeds",
                "1",
                "--repo-root",
                str(tmp_path / "repo"),
                "--generate-reference",
            ]
        )
    text = output.getvalue()
    assert rc == 0
    assert "WORKLOAD_ID=optical_scintillator" in text
    assert "WORKLOAD_ID=beam_neutron" in text
    assert "WORKLOAD_ID=W5" not in text
    assert "WORKLOAD_ID=W6" not in text
    assert "benchmark_optical_scintillator" in text
    assert "benchmark_beam_neutron" in text
    assert "COLLECTOR_NOT_IMPLEMENTED" not in text


def test_submit_dry_run_writes_valid_scripts_but_does_not_call_sbatch(tmp_path: Path) -> None:
    script_dir = tmp_path / "submit_scripts"
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


def test_reference_submit_dry_run_writes_vanilla_only_script(tmp_path: Path) -> None:
    script_dir = tmp_path / "reference_scripts"
    output = io.StringIO()
    with redirect_stdout(output):
        rc = run_main(
            [
                "--opt-id",
                "vanilla",
                "--workload",
                "optical_scintillator",
                "--physics-list",
                "PL1",
                "--hw",
                "H1",
                "--seed",
                "42",
                "--repo-root",
                str(tmp_path / "repo"),
                "--script-dir",
                str(script_dir),
                "--generate-reference",
                "--submit",
                "--dry-run",
            ]
        )
    assert rc == 0
    script = next(script_dir.glob("*.sbatch")).read_text(encoding="utf-8")
    assert "WORKLOAD_ID=optical_scintillator" in script
    assert "run_reference" in script
    assert "--collect --generate-reference" in script
    assert "run_one optimized" not in script
    assert "Submitted batch job" not in output.getvalue()


def test_collect_check_and_missing_raw_fail_closed(tmp_path: Path) -> None:
    output = io.StringIO()
    with redirect_stdout(output):
        ready_rc = run_main(["--collect", "--collect-check"])
    assert ready_rc == 0
    assert "COLLECT_READY" in output.getvalue()
    err = io.StringIO()
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    with redirect_stderr(err):
        rc = run_main(
            [
                "--collect",
                "--opt-id",
                "x",
                "--opt-branch",
                "lane/x",
                "--workload",
                "W1",
                "--physics-list",
                "PL1",
                "--hw",
                "H3",
                "--seeds",
                "1",
                "--raw-dir",
                str(raw_dir),
                "--slurm-job-id",
                "999",
            ]
        )
    assert rc == 2
    assert "missing raw file" in err.getvalue()


def test_collect_writes_result_row(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    for seed in (11, 22):
        _write_raw_pair(raw_dir, seed)
    results = tmp_path / "results/results.parquet"
    output = io.StringIO()
    with redirect_stdout(output):
        rc = run_main(
            [
                "--collect",
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
                "--n-events",
                "24",
                "--seeds",
                "11",
                "22",
                "--raw-dir",
                str(raw_dir),
                "--results",
                str(results),
                "--slurm-job-id",
                "999",
            ]
        )
    assert rc == 0
    assert "RESULT_COLLECTED" in output.getvalue()
    rows = read_rows(results)
    assert len(rows) == 1
    assert rows[0].workload_id == "W1"
    assert rows[0].speedup_mean == 2.0
    assert rows[0].parity_pass is True
    assert rows[0].result_tag == "SPEEDUP"


def test_reference_collect_writes_manifest(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    raw_dir = repo / "benchmarks/reference/optical_scintillator/PL1"
    raw_dir.mkdir(parents=True)
    for seed in (11, 22):
        pq.write_table(_raw_table(1_000_000_000, event_name="optical_scintillator"), raw_dir / f"seed_{seed}.parquet")
    output = io.StringIO()
    with redirect_stdout(output):
        rc = run_main(
            [
                "--collect",
                "--generate-reference",
                "--workload",
                "optical_scintillator",
                "--physics-list",
                "PL1",
                "--hw",
                "H1",
                "--n-events",
                "24",
                "--seeds",
                "11",
                "22",
                "--raw-dir",
                str(raw_dir),
                "--repo-root",
                str(repo),
                "--slurm-job-id",
                "999",
            ]
        )
    assert rc == 0
    manifest = repo / "benchmarks/reference/MANIFEST.sha256"
    text = manifest.read_text(encoding="utf-8")
    assert "optical_scintillator/PL1/seed_11.parquet" in text
    assert "optical_scintillator/PL1/seed_22.parquet" in text
    assert "REFERENCE_COLLECTED" in output.getvalue()


def test_reference_collect_rejects_superseded_w5_w6_directories(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    for workload, event_name in {"W5": "optical_scintillator", "W6": "beam_neutron"}.items():
        raw_dir = repo / f"benchmarks/reference/{workload}/PL1"
        raw_dir.mkdir(parents=True)
        pq.write_table(_raw_table(1_000_000_000, event_name=event_name), raw_dir / "seed_11.parquet")
        err = io.StringIO()
        with redirect_stderr(err):
            rc = run_main(
                [
                    "--collect",
                    "--generate-reference",
                    "--workload",
                    workload,
                    "--physics-list",
                    "PL1",
                    "--hw",
                    "H1",
                    "--n-events",
                    "24",
                    "--seeds",
                    "11",
                    "--raw-dir",
                    str(raw_dir),
                    "--repo-root",
                    str(repo),
                    "--slurm-job-id",
                    "999",
                ]
            )
        assert rc == 2
        assert "methodology-blocked" in err.getvalue()


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        test_module_help_exits_zero()
        test_dry_run_w1_pl1_h3_prints_sbatch_without_side_effects(tmp)
        run_bd001_registry_selftest(tmp / "bd001-registry-selftest")
        test_w5_w6_reference_dry_run_fail_closed_until_methodology_drivers_exist(tmp)
        test_stand_in_reference_dry_run_uses_event_names_not_methodology_ids(tmp)
        test_submit_dry_run_writes_valid_scripts_but_does_not_call_sbatch(tmp)
        test_reference_submit_dry_run_writes_vanilla_only_script(tmp)
        test_collect_check_and_missing_raw_fail_closed(tmp)
        test_collect_writes_result_row(tmp)
        test_reference_collect_writes_manifest(tmp)
        test_reference_collect_rejects_superseded_w5_w6_directories(tmp)
    print("benchmark_harness_run: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
