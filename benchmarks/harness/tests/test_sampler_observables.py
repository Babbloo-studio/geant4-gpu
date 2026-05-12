#!/usr/bin/env python3
"""Focused tests for BD-geant4-001 sampler-observable preflight gates."""

from __future__ import annotations

from pathlib import Path
import sys
import tempfile

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmarks.harness.sampler_observables import (  # noqa: E402
    BD001_REQUIRED_OBSERVABLES,
    SamplerObservableError,
    bd001_sampler_observable_gate,
)


def _write_sampler(path: Path, *, shifted: bool, aliases: bool = False, missing: str | None = None) -> None:
    n_rows = 512
    base = np.linspace(0.01, 0.99, n_rows)
    offset = 0.30 if shifted else 0.0
    columns = {
        "bd001_sampler_x": np.clip(base + offset, 0.0, 1.0),
        "bd001_delta_ray_ke_mev": 0.25 + 3.0 * base + (25.0 if shifted else 0.0),
        "bd001_delta_ray_theta_rad": 0.001 + 0.03 * base + (0.8 if shifted else 0.0),
        "bd001_downstream_dedx_mev_mm": 0.004 + 0.002 * base + (0.1 if shifted else 0.0),
    }
    if aliases:
        columns = {
            "sampler_x": columns["bd001_sampler_x"],
            "delta_ray_ke_mev": columns["bd001_delta_ray_ke_mev"],
            "delta_ray_theta_rad": columns["bd001_delta_ray_theta_rad"],
            "downstream_dedx_mev_mm": columns["bd001_downstream_dedx_mev_mm"],
        }
    if missing is not None:
        for key in list(columns):
            if missing in key:
                del columns[key]
                break
    pq.write_table(pa.Table.from_pydict(columns), path)


def test_bd001_sampler_observable_gate_identical_and_shifted(tmp_path: Path) -> None:
    reference = tmp_path / "reference.parquet"
    identical = tmp_path / "identical.parquet"
    shifted = tmp_path / "shifted.parquet"
    _write_sampler(reference, shifted=False)
    _write_sampler(identical, shifted=False, aliases=True)
    _write_sampler(shifted, shifted=True)

    same = bd001_sampler_observable_gate(reference, identical)
    assert same.passed, same.to_dict()
    assert tuple(same.ks_stats) == BD001_REQUIRED_OBSERVABLES
    assert all(value == 1.0 for value in same.ks_stats.values())

    different = bd001_sampler_observable_gate(reference, shifted)
    assert not different.passed
    assert {item.split("=", 1)[0] for item in different.failing_observables} == set(BD001_REQUIRED_OBSERVABLES)


def test_bd001_sampler_observable_gate_missing_column_fails_closed(tmp_path: Path) -> None:
    reference = tmp_path / "reference.parquet"
    missing = tmp_path / "missing.parquet"
    _write_sampler(reference, shifted=False)
    _write_sampler(missing, shifted=False, missing="theta")

    try:
        bd001_sampler_observable_gate(reference, missing)
    except SamplerObservableError as exc:
        message = str(exc)
        assert "BD-geant4-001 missing required sampler observable" in message
        assert "delta_ray_theta_rad" in message
    else:
        raise AssertionError("missing BD001 sampler observable was accepted")


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        test_bd001_sampler_observable_gate_identical_and_shifted(tmp)
        test_bd001_sampler_observable_gate_missing_column_fails_closed(tmp)
    print("benchmark_harness_sampler_observables: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
