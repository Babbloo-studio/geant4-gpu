#!/usr/bin/env python3
"""Convert a phase-5a benchmark CSV into a typed Parquet table."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

try:
    import pyarrow as pa
    import pyarrow.parquet as pq
except ImportError as exc:  # pragma: no cover - exercised on missing env only
    raise SystemExit(
        "pyarrow is required for G4GPU benchmark output; set "
        "G4GPU_BENCHMARK_PYTHON to the hibeam_env interpreter"
    ) from exc


SCHEMA = pa.schema(
    [
        ("event_name", pa.string()),
        ("event_label", pa.string()),
        ("geometry_id", pa.string()),
        ("geometry_material", pa.string()),
        ("event_id", pa.int32()),
        ("primary_pdg", pa.int32()),
        ("primary_ke_mev", pa.float64()),
        ("primary_px_mev", pa.float64()),
        ("primary_py_mev", pa.float64()),
        ("primary_pz_mev", pa.float64()),
        ("leading_particle_ke_mev", pa.float64()),
        ("total_deposited_energy_mev", pa.float64()),
        ("particle_multiplicity", pa.int32()),
        ("vertex_x_mm", pa.float64()),
        ("vertex_y_mm", pa.float64()),
        ("vertex_z_mm", pa.float64()),
        ("step_count", pa.int32()),
        ("hits", pa.int32()),
        ("hit_bin", pa.int32()),
        ("total_wall_time_ns", pa.int64()),
        ("per_step_time_ns", pa.float64()),
    ]
)

INT_FIELDS = {
    "event_id",
    "primary_pdg",
    "particle_multiplicity",
    "step_count",
    "hits",
    "hit_bin",
    "total_wall_time_ns",
}
FLOAT_FIELDS = {
    "primary_ke_mev",
    "primary_px_mev",
    "primary_py_mev",
    "primary_pz_mev",
    "leading_particle_ke_mev",
    "total_deposited_energy_mev",
    "vertex_x_mm",
    "vertex_y_mm",
    "vertex_z_mm",
    "per_step_time_ns",
}


def load_csv(path: Path) -> pa.Table:
    columns: dict[str, list[object]] = {field.name: [] for field in SCHEMA}
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        missing = set(columns) - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"missing benchmark columns: {sorted(missing)}")
        for row in reader:
            for name in columns:
                value = row[name]
                if name in INT_FIELDS:
                    columns[name].append(int(value))
                elif name in FLOAT_FIELDS:
                    columns[name].append(float(value))
                else:
                    columns[name].append(value)
    if not columns["event_id"]:
        raise ValueError("benchmark CSV contains no rows")
    return pa.Table.from_pydict(columns, schema=SCHEMA)


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: write_parquet.py input.csv output.parquet", file=sys.stderr)
        return 2
    input_csv = Path(argv[1])
    output_parquet = Path(argv[2])
    output_parquet.parent.mkdir(parents=True, exist_ok=True)
    table = load_csv(input_csv)
    pq.write_table(table, output_parquet, compression="zstd")
    print(f"wrote {table.num_rows} rows to {output_parquet}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
