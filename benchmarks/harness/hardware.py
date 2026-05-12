#!/usr/bin/env python3
"""Hardware fingerprinting helpers for the benchmark harness.

The functions in this module are intentionally side-effect light: local CPU/GPU
fingerprinting is safe, while SLURM evidence is collected from supplied text or
an explicitly injected command runner.  The benchmark runner remains the only
place that submits jobs.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import platform
import re
import socket
import subprocess
from typing import Mapping, Sequence


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EVIDENCE_DIR = REPO_ROOT / "benchmarks/hardware_evidence"
SAFE_JOB_ID = re.compile(r"^[A-Za-z0-9_.-]+$")


class HardwareError(RuntimeError):
    """Raised when hardware or scheduler evidence is malformed."""


@dataclass(frozen=True)
class CPUFingerprint:
    model_name: str
    logical_cpus: int
    physical_cores: int | None
    flags: tuple[str, ...]


@dataclass(frozen=True)
class GPUFingerprint:
    index: int
    name: str
    uuid: str
    memory_total_mb: int | None
    driver_version: str
    cuda_version: str


@dataclass(frozen=True)
class SlurmEvidence:
    job_id: str
    job_name: str | None
    partition: str | None
    node_list: str | None
    cpus_per_task: int | None
    gres: str | None
    account: str | None
    raw: str


@dataclass(frozen=True)
class HardwareFingerprint:
    hw_id: str
    hostname: str
    system: str
    kernel: str
    cpu: CPUFingerprint
    gpus: tuple[GPUFingerprint, ...]
    slurm: SlurmEvidence | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, indent=2)


def parse_cpuinfo(text: str) -> CPUFingerprint:
    """Parse Linux ``/proc/cpuinfo`` text into a compact CPU fingerprint."""

    records = _cpu_records(text)
    flags: set[str] = set()
    model = "unknown"
    physical_pairs: set[tuple[str, str]] = set()
    for record in records:
        if model == "unknown" and record.get("model name"):
            model = record["model name"]
        flags.update(record.get("flags", "").split())
        physical_id = record.get("physical id")
        core_id = record.get("core id")
        if physical_id is not None and core_id is not None:
            physical_pairs.add((physical_id, core_id))
    logical = len(records) if records else _positive_int(os.cpu_count()) or 1
    physical = len(physical_pairs) if physical_pairs else None
    return CPUFingerprint(model, logical, physical, tuple(sorted(flags)))


def parse_nvidia_smi_csv(text: str) -> tuple[GPUFingerprint, ...]:
    """Parse ``nvidia-smi --format=csv,noheader`` output."""

    gpus: list[GPUFingerprint] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        fields = [part.strip() for part in line.split(",")]
        if len(fields) < 6:
            raise HardwareError(f"expected 6 nvidia-smi CSV fields, got {len(fields)}: {line!r}")
        index = int(fields[0])
        memory = _parse_memory_mb(fields[3])
        gpus.append(GPUFingerprint(index, fields[1], fields[2], memory, fields[4], fields[5]))
    return tuple(gpus)


def slurm_from_env(env: Mapping[str, str] | None = None) -> SlurmEvidence | None:
    """Return scheduler evidence from SLURM environment variables, if present."""

    values = dict(os.environ if env is None else env)
    job_id = values.get("SLURM_JOB_ID")
    if not job_id:
        return None
    return SlurmEvidence(
        job_id=job_id,
        job_name=values.get("SLURM_JOB_NAME"),
        partition=values.get("SLURM_JOB_PARTITION"),
        node_list=values.get("SLURM_NODELIST") or values.get("SLURM_JOB_NODELIST"),
        cpus_per_task=_positive_int(values.get("SLURM_CPUS_PER_TASK")),
        gres=values.get("SLURM_JOB_GPUS") or values.get("SLURM_STEP_GPUS"),
        account=values.get("SLURM_JOB_ACCOUNT"),
        raw="\n".join(f"{key}={values[key]}" for key in sorted(values) if key.startswith("SLURM_")),
    )


def parse_scontrol_show_job(text: str) -> SlurmEvidence:
    """Parse a minimal ``scontrol show job`` transcript."""

    fields = dict(re.findall(r"([A-Za-z][A-Za-z0-9/]+)=(\S+)", text))
    job_id = fields.get("JobId") or fields.get("JobID")
    if not job_id:
        raise HardwareError("scontrol evidence is missing JobId")
    return SlurmEvidence(
        job_id=job_id,
        job_name=fields.get("JobName"),
        partition=fields.get("Partition"),
        node_list=fields.get("NodeList"),
        cpus_per_task=_positive_int(fields.get("CPUs/Task")),
        gres=fields.get("TresPerNode") or fields.get("Gres"),
        account=fields.get("Account"),
        raw=text,
    )


def write_slurm_evidence(job_id: str, text: str, evidence_dir: str | Path = DEFAULT_EVIDENCE_DIR) -> Path:
    """Write raw SLURM evidence under ``benchmarks/hardware_evidence``."""

    if not SAFE_JOB_ID.match(job_id):
        raise HardwareError(f"unsafe SLURM job id for evidence path: {job_id!r}")
    root = Path(evidence_dir)
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{job_id}.txt"
    path.write_text(text, encoding="utf-8")
    return path


def collect_slurm_evidence(
    job_id: str,
    *,
    evidence_dir: str | Path = DEFAULT_EVIDENCE_DIR,
    scontrol_text: str | None = None,
    run_command=subprocess.run,
    scontrol: str | Path = "scontrol",
    allow_command: bool = False,
) -> SlurmEvidence:
    """Collect and persist SLURM job evidence without submitting any job."""

    if scontrol_text is None:
        if not allow_command:
            raise HardwareError("live scontrol collection requires allow_command=True")
        proc = run_command(
            [str(scontrol), "show", "job", str(job_id)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            raise HardwareError(f"scontrol failed with rc={proc.returncode}: {proc.stdout.strip()}")
        scontrol_text = proc.stdout
    evidence = parse_scontrol_show_job(scontrol_text)
    if evidence.job_id != str(job_id):
        raise HardwareError(f"requested job {job_id!r}, but evidence is for {evidence.job_id!r}")
    write_slurm_evidence(evidence.job_id, scontrol_text, evidence_dir)
    return evidence


def collect_local_fingerprint(
    hw_id: str,
    *,
    cpuinfo_path: str | Path = "/proc/cpuinfo",
    env: Mapping[str, str] | None = None,
    run_command=subprocess.run,
    nvidia_smi: str | Path = "nvidia-smi",
) -> HardwareFingerprint:
    """Collect CPU/GPU/SLURM environment evidence for the current node."""

    cpu_text = Path(cpuinfo_path).read_text(encoding="utf-8", errors="replace")
    gpus = _query_nvidia_smi(run_command, nvidia_smi)
    return HardwareFingerprint(
        hw_id=hw_id,
        hostname=socket.gethostname(),
        system=platform.platform(),
        kernel=platform.release(),
        cpu=parse_cpuinfo(cpu_text),
        gpus=gpus,
        slurm=slurm_from_env(env),
    )


def _query_nvidia_smi(run_command, nvidia_smi: str | Path) -> tuple[GPUFingerprint, ...]:
    command = [
        str(nvidia_smi),
        "--query-gpu=index,name,uuid,memory.total,driver_version,cuda_version",
        "--format=csv,noheader,nounits",
    ]
    try:
        proc = run_command(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return ()
    if proc.returncode != 0 or not proc.stdout.strip():
        return ()
    return parse_nvidia_smi_csv(proc.stdout)


def _cpu_records(text: str) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            if current:
                records.append(current)
                current = {}
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        current[key.strip()] = value.strip()
    if current:
        records.append(current)
    return records


def _parse_memory_mb(value: str) -> int | None:
    match = re.search(r"(\d+)", value)
    return int(match.group(1)) if match else None


def _positive_int(value: object) -> int | None:
    try:
        parsed = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


__all__ = [
    "CPUFingerprint",
    "GPUFingerprint",
    "HardwareError",
    "HardwareFingerprint",
    "SlurmEvidence",
    "collect_local_fingerprint",
    "collect_slurm_evidence",
    "parse_cpuinfo",
    "parse_nvidia_smi_csv",
    "parse_scontrol_show_job",
    "slurm_from_env",
    "write_slurm_evidence",
]
