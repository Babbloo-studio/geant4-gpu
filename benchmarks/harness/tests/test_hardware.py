#!/usr/bin/env python3
"""Focused tests for benchmark-harness hardware.py fingerprint helpers."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmarks.harness.hardware import (  # noqa: E402
    HardwareError,
    collect_local_fingerprint,
    collect_slurm_evidence,
    parse_cpuinfo,
    parse_nvidia_smi_csv,
    parse_scontrol_show_job,
    slurm_from_env,
    write_slurm_evidence,
)


CPUINFO = """processor   : 0
model name  : Mock CPU 9000
physical id : 0
core id     : 0
flags       : fpu avx avx2

processor   : 1
model name  : Mock CPU 9000
physical id : 0
core id     : 1
flags       : fpu avx avx512f
"""


def test_parse_cpuinfo_counts_and_flags() -> None:
    cpu = parse_cpuinfo(CPUINFO)
    assert cpu.model_name == "Mock CPU 9000"
    assert cpu.logical_cpus == 2
    assert cpu.physical_cores == 2
    assert cpu.flags == ("avx", "avx2", "avx512f", "fpu")


def test_parse_nvidia_smi_csv() -> None:
    gpus = parse_nvidia_smi_csv("0, NVIDIA A40, GPU-deadbeef, 46068, 550.54, 12.4\n")
    assert len(gpus) == 1
    assert gpus[0].index == 0
    assert gpus[0].name == "NVIDIA A40"
    assert gpus[0].memory_total_mb == 46068


def test_slurm_env_and_scontrol_parsing() -> None:
    env = {
        "SLURM_JOB_ID": "12345",
        "SLURM_JOB_NAME": "g4gpu-harness",
        "SLURM_JOB_PARTITION": "gpua40",
        "SLURM_NODELIST": "cg14",
        "SLURM_CPUS_PER_TASK": "4",
        "SLURM_JOB_ACCOUNT": "lu2026-2-51",
    }
    evidence = slurm_from_env(env)
    assert evidence is not None
    assert evidence.job_id == "12345"
    assert evidence.cpus_per_task == 4
    parsed = parse_scontrol_show_job(
        "JobId=12345 JobName=g4gpu-harness Partition=gpua40 "
        "Account=lu2026-2-51 NodeList=cg14 CPUs/Task=4 TresPerNode=gpu:a40:1"
    )
    assert parsed.job_id == "12345"
    assert parsed.gres == "gpu:a40:1"


def test_collect_slurm_evidence_writes_supplied_text_only(tmp_path: Path) -> None:
    raw = "JobId=12345 JobName=g4gpu Partition=lu48 NodeList=cn018 CPUs/Task=2"
    evidence = collect_slurm_evidence("12345", scontrol_text=raw, evidence_dir=tmp_path)
    assert evidence.job_id == "12345"
    assert (tmp_path / "12345.txt").read_text(encoding="utf-8") == raw
    try:
        write_slurm_evidence("../bad", raw, tmp_path)
    except HardwareError as exc:
        assert "unsafe" in str(exc)
    else:
        raise AssertionError("unsafe job id was accepted")


class _FakeProc:
    def __init__(self, returncode: int, stdout: str):
        self.returncode = returncode
        self.stdout = stdout


def test_collect_local_fingerprint_uses_mocked_nvidia_smi(tmp_path: Path) -> None:
    cpuinfo = tmp_path / "cpuinfo"
    cpuinfo.write_text(CPUINFO, encoding="utf-8")

    def fake_run(command, **kwargs):  # noqa: ANN001
        assert "nvidia-smi" in command[0]
        return _FakeProc(0, "0, NVIDIA A40, GPU-deadbeef, 46068, 550.54, 12.4\n")

    fingerprint = collect_local_fingerprint(
        "H3",
        cpuinfo_path=cpuinfo,
        env={"SLURM_JOB_ID": "222", "SLURM_JOB_NAME": "mock"},
        run_command=fake_run,
    )
    assert fingerprint.hw_id == "H3"
    assert fingerprint.cpu.logical_cpus == 2
    assert len(fingerprint.gpus) == 1
    assert fingerprint.slurm is not None
    assert fingerprint.slurm.job_id == "222"
    assert '"hw_id": "H3"' in fingerprint.to_json()


def test_collect_slurm_evidence_can_mock_command(tmp_path: Path) -> None:
    def fake_scontrol(command, **kwargs):  # noqa: ANN001
        assert command[:3] == ["scontrol", "show", "job"]
        return _FakeProc(0, "JobId=123 JobName=mock Partition=lu48 NodeList=cn018")

    evidence = collect_slurm_evidence(
        "123",
        evidence_dir=tmp_path,
        allow_command=True,
        run_command=fake_scontrol,
    )
    assert evidence.node_list == "cn018"
    assert (tmp_path / "123.txt").exists()


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        test_parse_cpuinfo_counts_and_flags()
        test_parse_nvidia_smi_csv()
        test_slurm_env_and_scontrol_parsing()
        test_collect_slurm_evidence_writes_supplied_text_only(tmp)
        test_collect_local_fingerprint_uses_mocked_nvidia_smi(tmp)
        test_collect_slurm_evidence_can_mock_command(tmp)
    print("benchmark_harness_hardware: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
