#!/usr/bin/env python3
"""Focused tests for benchmark-harness schema.py and parity.py."""

from __future__ import annotations

import tempfile
from pathlib import Path
import sys

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmarks.harness.parity import parity_gate  # noqa: E402
from benchmarks.harness.schema import (  # noqa: E402
    BenchmarkResultRow,
    COLUMN_NAMES,
    RESULT_SCHEMA,
    read_rows,
    result_tag_for,
    table_from_rows,
    utc_timestamp,
    write_rows,
)


OBS_SCHEMA = pa.schema(
    [
        ("edep_total", pa.float64()),
        ("step_count", pa.int32()),
        ("secondary_multiplicity", pa.int32()),
        ("first_step_length", pa.float64()),
    ]
)


def _example_row() -> BenchmarkResultRow:
    return BenchmarkResultRow(
        opt_id="BD-geant4-032",
        opt_branch="lane/test",
        opt_cmake_flags="-DG4GPU_TEST=ON",
        workload_id="W1",
        physics_list="PL1",
        hw_id="H3",
        slurm_job_id="dry-run",
        geant4_version="v11.2.2",
        n_events=1000,
        n_seeds=2,
        seeds=[101, 202],
        wall_s_vanilla=12.0,
        wall_s_opt=10.0,
        wall_s_vanilla_std=0.2,
        wall_s_opt_std=0.1,
        speedup_mean=1.2,
        speedup_ci95_lo=1.04,
        speedup_ci95_hi=1.36,
        steps_per_event_vanilla=40.0,
        steps_per_event_opt=40.0,
        ks_edep_p=1.0,
        ks_stepcount_p=1.0,
        ks_secondary_p=1.0,
        ks_firststepl_p=1.0,
        ks_neutron_p=None,
        parity_pass=True,
        claim_level="L0",
        result_tag="SPEEDUP",
        perf_instructions=None,
        perf_cache_misses=None,
        notes="",
        timestamp=utc_timestamp(),
    )


def _write_observables(path: Path, *, shifted: bool) -> None:
    n_rows = 256
    base = np.linspace(0.0, 1.0, n_rows)
    offset = 50.0 if shifted else 0.0
    table = pa.Table.from_pydict(
        {
            "edep_total": 10.0 + base + offset,
            "step_count": (100 + np.arange(n_rows) % 7 + int(offset)).astype(np.int32),
            "secondary_multiplicity": (2 + np.arange(n_rows) % 5 + int(offset)).astype(np.int32),
            "first_step_length": 0.1 + 0.01 * base + offset,
        },
        schema=OBS_SCHEMA,
    )
    pq.write_table(table, path)


def test_schema_round_trip(tmp: Path) -> None:
    row = _example_row()
    table = table_from_rows([row])
    assert table.schema.equals(RESULT_SCHEMA, check_metadata=False)
    assert tuple(table.column_names) == COLUMN_NAMES
    assert table["seeds"][0].as_py() == [101, 202]
    path = tmp / "result.parquet"
    write_rows(path, [row])
    assert read_rows(path) == [row]
    assert result_tag_for(1.01, True) == "SPEEDUP"
    assert result_tag_for(0.97, True) == "NEUTRAL"
    assert result_tag_for(0.90, True) == "REGRESSION"
    assert result_tag_for(99.0, False) == "PARITY_FAIL"


def test_parity_identical_and_shifted(tmp: Path) -> None:
    reference = tmp / "reference.parquet"
    identical = tmp / "identical.parquet"
    shifted = tmp / "shifted.parquet"
    _write_observables(reference, shifted=False)
    _write_observables(identical, shifted=False)
    _write_observables(shifted, shifted=True)

    same = parity_gate(reference, identical)
    assert same.passed
    for name in ("edep_total", "step_count", "secondary_multiplicity", "first_step_length"):
        assert same.ks_stats[name] == 1.0, same.to_dict()
    assert same.ks_stats["neutron_capture_rate"] is None
    assert same.skipped_observables == ["neutron_capture_rate"]

    different = parity_gate(reference, shifted)
    assert not different.passed
    assert different.failing_observables
    assert min(value for value in different.ks_stats.values() if value is not None) < 0.05


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        test_schema_round_trip(tmp)
        test_parity_identical_and_shifted(tmp)
    print("benchmark_harness_schema_parity: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
