#!/usr/bin/env python3
"""Verify the BD-geant4-001 sampler-observable preflight artifacts."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
MODULE = ROOT / "benchmarks/harness/sampler_observables.py"
TEST = ROOT / "benchmarks/harness/tests/test_sampler_observables.py"
CMAKE = ROOT / "CMakeLists.txt"
INIT = ROOT / "benchmarks/harness/__init__.py"
REPORT = ROOT / "docs/reports/bd_geant4_001_sampler_observables_preflight_20260512.md"


def _read(path: Path) -> str:
    if not path.is_file():
        raise AssertionError(f"missing required file: {path}")
    return path.read_text(encoding="utf-8")


def _require_markers(path: Path, markers: tuple[str, ...]) -> None:
    text = _read(path)
    missing = [marker for marker in markers if marker not in text]
    if missing:
        raise AssertionError(f"{path} missing markers: {missing}")


def _run(cmd: list[str]) -> str:
    proc = subprocess.run(cmd, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    if proc.returncode != 0:
        raise AssertionError(f"command failed ({proc.returncode}): {' '.join(cmd)}\n{proc.stdout}")
    return proc.stdout


def _write(path: Path, *, shifted: bool, missing_theta: bool = False) -> None:
    base = np.linspace(0.01, 0.99, 128)
    offset = 0.5 if shifted else 0.0
    data = {
        "bd001_sampler_x": np.clip(base + offset, 0.0, 1.0),
        "bd001_delta_ray_ke_mev": 0.1 + base + 10.0 * offset,
        "bd001_delta_ray_theta_rad": 0.01 + base + offset,
        "bd001_downstream_dedx_mev_mm": 0.001 + 0.01 * base + offset,
    }
    if missing_theta:
        del data["bd001_delta_ray_theta_rad"]
    pq.write_table(pa.Table.from_pydict(data), path)


def _exercise_gate() -> None:
    from benchmarks.harness.sampler_observables import SamplerObservableError, bd001_sampler_observable_gate

    with tempfile.TemporaryDirectory(prefix="bd001-sampler-preflight-") as tmp_s:
        tmp = Path(tmp_s)
        ref = tmp / "ref.parquet"
        same = tmp / "same.parquet"
        shifted = tmp / "shifted.parquet"
        missing = tmp / "missing.parquet"
        _write(ref, shifted=False)
        _write(same, shifted=False)
        _write(shifted, shifted=True)
        _write(missing, shifted=False, missing_theta=True)
        identical = bd001_sampler_observable_gate(ref, same)
        if not identical.passed or set(identical.ks_stats) != {
            "sampler_x",
            "delta_ray_ke_mev",
            "delta_ray_theta_rad",
            "downstream_dedx_mev_mm",
        }:
            raise AssertionError(f"identical sampler gate did not pass: {identical.to_dict()}")
        different = bd001_sampler_observable_gate(ref, shifted)
        if different.passed or not different.failing_observables:
            raise AssertionError(f"shifted sampler gate did not fail: {different.to_dict()}")
        try:
            bd001_sampler_observable_gate(ref, missing)
        except SamplerObservableError as exc:
            if "delta_ray_theta_rad" not in str(exc):
                raise AssertionError(f"missing-column error lacked theta marker: {exc}") from exc
        else:
            raise AssertionError("missing theta sampler observable was accepted")


def main() -> int:
    _require_markers(
        MODULE,
        (
            "BD001_OBSERVABLE_ALIASES",
            "sampler_x",
            "delta_ray_ke_mev",
            "delta_ray_theta_rad",
            "downstream_dedx_mev_mm",
            "SamplerObservableError",
            "bd001_sampler_observable_gate",
        ),
    )
    print("SAMPLER_MODULE_MARKERS_OK")
    _require_markers(TEST, ("test_bd001_sampler_observable_gate_identical_and_shifted", "missing_column"))
    _require_markers(INIT, ("SamplerObservableGateResult", "bd001_sampler_observable_gate"))
    _require_markers(CMAKE, ("g4gpu_benchmark_harness_sampler_observables", "test_sampler_observables.py"))
    print("SAMPLER_REGISTRATION_MARKERS_OK")
    _exercise_gate()
    print("SAMPLER_GATE_EXERCISE_OK")
    output = _run([sys.executable, "benchmarks/harness/tests/test_sampler_observables.py"])
    if "benchmark_harness_sampler_observables: PASS" not in output:
        raise AssertionError(output)
    print("SAMPLER_DIRECT_TEST_OK")
    _require_markers(
        REPORT,
        (
            "BD-geant4-001 sampler-observable preflight",
            "No SLURM",
            "result row",
            "BD001_SAMPLER_OBSERVABLES_PREFLIGHT_OK",
        ),
    )
    print("SAMPLER_REPORT_MARKERS_OK")
    print("BD001_SAMPLER_OBSERVABLES_PREFLIGHT_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
