#!/usr/bin/env python3
"""Smoke-test the phase-5 validation harness without pre-existing results."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq


SCHEMA = pa.schema(
    [
        ("total_deposited_energy_mev", pa.float64()),
        ("leading_particle_ke_mev", pa.float64()),
        ("particle_multiplicity", pa.int32()),
        ("vertex_x_mm", pa.float64()),
        ("vertex_y_mm", pa.float64()),
        ("vertex_z_mm", pa.float64()),
    ]
)


def _load_validate_module(path: Path):
    spec = importlib.util.spec_from_file_location("g4gpu_phase5_validate", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import validation harness from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_table(path: Path, *, shifted: bool) -> None:
    n_rows = 128
    base = np.linspace(0.0, 1.0, n_rows)
    offset = 20.0 if shifted else 0.0
    table = pa.Table.from_pydict(
        {
            "total_deposited_energy_mev": 10.0 + base + offset,
            "leading_particle_ke_mev": 100.0 - base - offset,
            "particle_multiplicity": (1 + np.arange(n_rows) % 5 + (20 if shifted else 0))
            .astype(np.int32),
            "vertex_x_mm": base + offset,
            "vertex_y_mm": 0.5 * base + offset,
            "vertex_z_mm": 0.25 * base + offset,
        },
        schema=SCHEMA,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, path)


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: validate_self_test.py validate.py output-dir", file=sys.stderr)
        return 2
    validate = _load_validate_module(Path(argv[1]))
    out_dir = Path(argv[2])
    reference = out_dir / "reference.parquet"
    identical = out_dir / "identical.parquet"
    shifted = out_dir / "shifted.parquet"
    _write_table(reference, shifted=False)
    _write_table(identical, shifted=False)
    _write_table(shifted, shifted=True)

    same = validate.compare_files(reference, identical, bins=16)
    different = validate.compare_files(reference, shifted, bins=16)
    if not same.passed:
        raise AssertionError("identical validation comparison should pass")
    if different.passed:
        raise AssertionError("shifted validation comparison should fail")
    print("validate_self_test: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
