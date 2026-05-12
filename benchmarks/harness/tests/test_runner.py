#!/usr/bin/env python3
"""Focused tests for benchmark-harness runner.py dry-run SLURM scripts."""

from __future__ import annotations

from contextlib import redirect_stdout
from dataclasses import replace
import io
from pathlib import Path
import stat
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmarks.harness.runner import (  # noqa: E402
    RunnerError,
    RunnerSpec,
    main as runner_main,
    render_sbatch,
    submit_sbatch,
    write_sbatch,
)
from benchmarks.harness.builder import BuildError  # noqa: E402


def _spec(tmp: Path) -> RunnerSpec:
    return RunnerSpec(
        opt_id="BD-geant4-032",
        opt_branch="lane/bd-geant4-032",
        workload="W1",
        physics_list="PL1",
        hw_id="H3",
        seeds=(101, 202),
        n_events=17,
        repo_root=tmp / "repo",
        geant4_prefix=tmp / "hibeam_env",
        python=Path("/usr/bin/python3"),
        vanilla_build=tmp / "builds/vanilla",
        optimized_build=tmp / "builds/optimized",
        raw_root=tmp / "raw",
        results_path=tmp / "results/results.parquet",
    )


def test_render_sbatch_contains_fail_closed_compute_node_contract(tmp_path: Path) -> None:
    script = render_sbatch(_spec(tmp_path))
    assert "#SBATCH --account=lu2026-2-51" in script
    assert "module load GCC/13.2.0 CUDA/12.8.0 CMake/3.27.6" in script
    assert '[[ -z "${SLURM_JOB_ID:-}" ]]' in script
    assert "must be launched with sbatch" in script
    assert "COLLECTOR_NOT_IMPLEMENTED" not in script
    assert "benchmarks.harness.run --collect --collect-check" in script
    assert "run_one vanilla" in script
    assert "run_one optimized" in script
    assert '${variant}_seed_${seed}.txt' in script
    assert '${variant}_seed_${seed}.parquet' in script
    assert "benchmark_gamma_100mev" in script
    assert "VANILLA_GEANT4_PREFIX=" in script
    assert "OPTIMIZED_GEANT4_PREFIX=" in script
    assert 'setup_geant4_env "${geant4_prefix}"' in script
    assert '"${binary}" --events "${N_EVENTS}" --commit "${OPT_ID}_${variant}_seed_${seed}" \\' in script
    assert '    --physics-list "${PHYSICS_LIST}" --output "${out}"' in script


def test_bd001_requires_distinct_optimized_geant4_prefix(tmp_path: Path) -> None:
    try:
        render_sbatch(replace(_spec(tmp_path), opt_id="BD-geant4-001", opt_branch="lane/bd001"))
    except RunnerError as exc:
        assert "explicit optimized_geant4_prefix" in str(exc)
    else:
        raise AssertionError("BD-001 rendered without an optimized Geant4 prefix")

    try:
        render_sbatch(
            replace(
                _spec(tmp_path),
                opt_id="BD-geant4-001",
                opt_branch="lane/bd001",
                optimized_geant4_prefix=tmp_path / "hibeam_env",
            )
        )
    except RunnerError as exc:
        assert "must differ" in str(exc)
    else:
        raise AssertionError("BD-001 rendered with identical vanilla/optimized Geant4 prefixes")


def test_bd001_renders_separate_optimized_geant4_prefix(tmp_path: Path) -> None:
    script = render_sbatch(
        replace(
            _spec(tmp_path),
            opt_id="BD-geant4-001",
            opt_branch="lane/bd001",
            optimized_geant4_prefix=tmp_path / "optimized-geant4",
        )
    )
    assert f"VANILLA_GEANT4_PREFIX={tmp_path / 'hibeam_env'}" in script
    assert f"OPTIMIZED_GEANT4_PREFIX={tmp_path / 'optimized-geant4'}" in script
    assert 'run_one vanilla "${VANILLA_BIN}" "${seed}" "${VANILLA_GEANT4_PREFIX}"' in script
    assert 'run_one optimized "${OPTIMIZED_BIN}" "${seed}" "${OPTIMIZED_GEANT4_PREFIX}"' in script


def test_render_reference_mode_runs_vanilla_only_for_stand_in_event(tmp_path: Path) -> None:
    script = render_sbatch(replace(_spec(tmp_path), reference_mode=True, workload="optical_scintillator"))
    assert "WORKLOAD_ID=optical_scintillator" in script
    assert "benchmark_optical_scintillator" in script
    assert "run_reference" in script
    assert '"${VANILLA_BIN}" --events "${N_EVENTS}" --commit "reference_${WORKLOAD_ID}_${PHYSICS_LIST}_seed_${seed}" \\' in script
    assert '    --physics-list "${PHYSICS_LIST}" --output "${out}"' in script
    assert "seed_${seed}.parquet" in script
    assert "--collect --generate-reference" in script
    assert "run_one optimized" not in script
    assert "missing executable optimized binary" not in script


def test_render_methodology_w5_w6_fail_closed(tmp_path: Path) -> None:
    for workload in ("W5", "W6"):
        try:
            render_sbatch(replace(_spec(tmp_path), reference_mode=True, workload=workload))
        except BuildError as exc:
            assert "methodology-blocked" in str(exc)
            assert "NNBAR full event" in str(exc)
            assert "docs/specs/w5_w6_full_event_drivers.md" in str(exc)
        else:
            raise AssertionError(f"{workload} rendered despite missing true NNBAR full-event driver")



def test_write_sbatch_is_bash_syntax_clean(tmp_path: Path) -> None:
    path = write_sbatch(_spec(tmp_path), tmp_path / "runner.sbatch")
    mode = path.stat().st_mode
    assert mode & stat.S_IXUSR
    proc = subprocess.run(
        ["bash", "-n", str(path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout


def test_submit_dry_run_does_not_call_sbatch(tmp_path: Path) -> None:
    path = write_sbatch(_spec(tmp_path), tmp_path / "runner.sbatch")
    job_id = submit_sbatch(path, dry_run=True, sbatch=tmp_path / "missing-sbatch")
    assert job_id == f"DRY_RUN {path}"


def test_submit_parses_fake_sbatch_job_id(tmp_path: Path) -> None:
    path = write_sbatch(_spec(tmp_path), tmp_path / "runner.sbatch")
    fake_sbatch = tmp_path / "sbatch"
    fake_sbatch.write_text(
        "#!/usr/bin/env bash\n"
        "printf 'Submitted batch job 123456\\n'\n",
        encoding="utf-8",
    )
    fake_sbatch.chmod(0o755)
    assert submit_sbatch(path, sbatch=fake_sbatch) == "123456"


def test_cli_submit_dry_run_prints_valid_script(tmp_path: Path) -> None:
    script_path = tmp_path / "cli-runner.sbatch"
    output = io.StringIO()
    with redirect_stdout(output):
        rc = runner_main(
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
                "--seed",
                "101",
                "--n-events",
                "3",
                "--repo-root",
                str(tmp_path / "repo"),
                "--geant4-prefix",
                str(tmp_path / "hibeam_env"),
                "--python",
                "/usr/bin/python3",
                "--vanilla-build",
                str(tmp_path / "builds/vanilla"),
                "--optimized-build",
                str(tmp_path / "builds/optimized"),
                "--script",
                str(script_path),
                "--submit",
                "--dry-run",
                "--sbatch",
                str(tmp_path / "missing-sbatch"),
            ]
        )
    assert rc == 0
    printed = output.getvalue()
    assert "Submitted batch job" not in printed
    assert "#SBATCH --job-name=g4gpu-BD-geant4-032-W1" in printed
    assert script_path.is_file()
    proc = subprocess.run(["bash", "-n", str(script_path)], check=False)
    assert proc.returncode == 0


def test_cli_dry_run_without_script_has_no_repo_side_effect(tmp_path: Path) -> None:
    output = io.StringIO()
    with redirect_stdout(output):
        rc = runner_main(
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
                "--seed",
                "101",
                "--repo-root",
                str(tmp_path / "repo"),
                "--geant4-prefix",
                str(tmp_path / "hibeam_env"),
                "--python",
                "/usr/bin/python3",
                "--vanilla-build",
                str(tmp_path / "builds/vanilla"),
                "--optimized-build",
                str(tmp_path / "builds/optimized"),
                "--submit",
                "--dry-run",
            ]
        )
    assert rc == 0
    assert "#SBATCH" in output.getvalue()
    assert not (tmp_path / "repo/benchmarks/raw/BD-geant4-032/run.sbatch").exists()


def test_invalid_seed_fails_closed(tmp_path: Path) -> None:
    try:
        render_sbatch(replace(_spec(tmp_path), seeds=(-1,)))
    except RunnerError as exc:
        assert "seeds must be non-negative" in str(exc)
    else:
        raise AssertionError("runner accepted a negative seed")


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        test_render_sbatch_contains_fail_closed_compute_node_contract(tmp)
        test_bd001_requires_distinct_optimized_geant4_prefix(tmp)
        test_bd001_renders_separate_optimized_geant4_prefix(tmp)
        test_render_reference_mode_runs_vanilla_only_for_stand_in_event(tmp)
        test_render_methodology_w5_w6_fail_closed(tmp)
        test_write_sbatch_is_bash_syntax_clean(tmp)
        test_submit_dry_run_does_not_call_sbatch(tmp)
        test_submit_parses_fake_sbatch_job_id(tmp)
        test_cli_submit_dry_run_prints_valid_script(tmp)
        test_cli_dry_run_without_script_has_no_repo_side_effect(tmp)
        test_invalid_seed_fails_closed(tmp)
    print("benchmark_harness_runner: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
