#!/usr/bin/env python3
"""Parquet row schema for the G4GPU benchmark harness.

This module is the single source of truth for rows appended to
``benchmarks/results/results.parquet``.  It deliberately keeps the contract
small: callers construct :class:`BenchmarkResultRow`, convert rows to a typed
PyArrow table, and then write or append that table in higher-level harness
code.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from datetime import datetime, timezone
from math import isfinite
from pathlib import Path
from typing import Any, Iterable

import pyarrow as pa
import pyarrow.parquet as pq

CLAIM_LEVELS = frozenset({"L0", "L1", "L2", "L3", "L4"})
RESULT_TAGS = frozenset({"SPEEDUP", "NEUTRAL", "REGRESSION", "PARITY_FAIL"})

RESULT_FIELDS = (
    pa.field("opt_id", pa.string(), nullable=False),
    pa.field("opt_branch", pa.string(), nullable=False),
    pa.field("opt_cmake_flags", pa.string(), nullable=False),
    pa.field("workload_id", pa.string(), nullable=False),
    pa.field("physics_list", pa.string(), nullable=False),
    pa.field("hw_id", pa.string(), nullable=False),
    pa.field("slurm_job_id", pa.string(), nullable=False),
    pa.field("geant4_version", pa.string(), nullable=False),
    pa.field("n_events", pa.int64(), nullable=False),
    pa.field("n_seeds", pa.int64(), nullable=False),
    pa.field("seeds", pa.list_(pa.int64()), nullable=False),
    pa.field("wall_s_vanilla", pa.float64(), nullable=False),
    pa.field("wall_s_opt", pa.float64(), nullable=False),
    pa.field("wall_s_vanilla_std", pa.float64(), nullable=False),
    pa.field("wall_s_opt_std", pa.float64(), nullable=False),
    pa.field("speedup_mean", pa.float64(), nullable=False),
    pa.field("speedup_ci95_lo", pa.float64(), nullable=False),
    pa.field("speedup_ci95_hi", pa.float64(), nullable=False),
    pa.field("steps_per_event_vanilla", pa.float64(), nullable=False),
    pa.field("steps_per_event_opt", pa.float64(), nullable=False),
    pa.field("ks_edep_p", pa.float64(), nullable=False),
    pa.field("ks_stepcount_p", pa.float64(), nullable=False),
    pa.field("ks_secondary_p", pa.float64(), nullable=False),
    pa.field("ks_firststepl_p", pa.float64(), nullable=False),
    pa.field("ks_neutron_p", pa.float64(), nullable=True),
    pa.field("parity_pass", pa.bool_(), nullable=False),
    pa.field("claim_level", pa.string(), nullable=False),
    pa.field("result_tag", pa.string(), nullable=False),
    pa.field("perf_instructions", pa.float64(), nullable=True),
    pa.field("perf_cache_misses", pa.float64(), nullable=True),
    pa.field("notes", pa.string(), nullable=False),
    pa.field("timestamp", pa.string(), nullable=False),
)

RESULT_SCHEMA = pa.schema(RESULT_FIELDS)
COLUMN_NAMES = tuple(field.name for field in RESULT_FIELDS)
OPTIONAL_FLOAT_COLUMNS = frozenset({"ks_neutron_p", "perf_instructions", "perf_cache_misses"})


@dataclass(frozen=True)
class BenchmarkResultRow:
    opt_id: str
    opt_branch: str
    opt_cmake_flags: str
    workload_id: str
    physics_list: str
    hw_id: str
    slurm_job_id: str
    geant4_version: str
    n_events: int
    n_seeds: int
    seeds: list[int]
    wall_s_vanilla: float
    wall_s_opt: float
    wall_s_vanilla_std: float
    wall_s_opt_std: float
    speedup_mean: float
    speedup_ci95_lo: float
    speedup_ci95_hi: float
    steps_per_event_vanilla: float
    steps_per_event_opt: float
    ks_edep_p: float
    ks_stepcount_p: float
    ks_secondary_p: float
    ks_firststepl_p: float
    ks_neutron_p: float | None
    parity_pass: bool
    claim_level: str
    result_tag: str
    perf_instructions: float | None
    perf_cache_misses: float | None
    notes: str
    timestamp: str

    def __post_init__(self) -> None:
        validate_row(self)

    def to_record(self) -> dict[str, Any]:
        record = asdict(self)
        record["seeds"] = [int(seed) for seed in self.seeds]
        return record

    @classmethod
    def from_record(cls, record: dict[str, Any]) -> "BenchmarkResultRow":
        extra = set(record) - set(COLUMN_NAMES)
        missing = set(COLUMN_NAMES) - set(record)
        if extra or missing:
            raise ValueError(f"benchmark row schema mismatch: extra={sorted(extra)} missing={sorted(missing)}")
        payload = dict(record)
        payload["seeds"] = [int(seed) for seed in payload["seeds"]]
        return cls(**payload)


def utc_timestamp() -> str:
    """Return an ISO-8601 UTC timestamp accepted by the harness schema."""

    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def result_tag_for(speedup_ci95_lo: float, parity_pass: bool) -> str:
    """Classify a result row using the benchmark-harness interpretation rules."""

    if not parity_pass:
        return "PARITY_FAIL"
    if speedup_ci95_lo > 1.0:
        return "SPEEDUP"
    if speedup_ci95_lo >= 0.95:
        return "NEUTRAL"
    return "REGRESSION"


def validate_row(row: BenchmarkResultRow) -> None:
    if [field.name for field in fields(row)] != list(COLUMN_NAMES):
        raise ValueError("BenchmarkResultRow field order does not match RESULT_SCHEMA")
    if row.n_events <= 0:
        raise ValueError("n_events must be positive")
    if row.n_seeds != len(row.seeds):
        raise ValueError("n_seeds must equal len(seeds)")
    if row.n_seeds <= 0:
        raise ValueError("n_seeds must be positive")
    if any(not isinstance(seed, int) for seed in row.seeds):
        raise ValueError("seeds must be integers")
    if row.claim_level not in CLAIM_LEVELS:
        raise ValueError(f"claim_level must be one of {sorted(CLAIM_LEVELS)}")
    if row.result_tag not in RESULT_TAGS:
        raise ValueError(f"result_tag must be one of {sorted(RESULT_TAGS)}")
    expected_tag = result_tag_for(row.speedup_ci95_lo, row.parity_pass)
    if row.result_tag != expected_tag:
        raise ValueError(f"result_tag={row.result_tag} disagrees with expected {expected_tag}")
    for name in COLUMN_NAMES:
        value = getattr(row, name)
        if name in OPTIONAL_FLOAT_COLUMNS and value is None:
            continue
        if RESULT_SCHEMA.field(name).type == pa.float64() and not isfinite(float(value)):
            raise ValueError(f"{name} must be finite")
    for name in ("opt_id", "opt_branch", "workload_id", "physics_list", "hw_id", "geant4_version", "timestamp"):
        if not str(getattr(row, name)):
            raise ValueError(f"{name} must be non-empty")
    if row.notes and row.claim_level == "L3":
        raise ValueError("notes must be empty for L3 rows")


def table_from_rows(rows: Iterable[BenchmarkResultRow]) -> pa.Table:
    records = [row.to_record() for row in rows]
    if not records:
        return RESULT_SCHEMA.empty_table()
    table = pa.Table.from_pylist(records, schema=RESULT_SCHEMA)
    validate_table(table)
    return table


def validate_table(table: pa.Table) -> None:
    if not table.schema.equals(RESULT_SCHEMA, check_metadata=False):
        raise ValueError(f"unexpected benchmark result schema: {table.schema}")
    for record in table.to_pylist():
        BenchmarkResultRow.from_record(record)


def write_rows(path: Path, rows: Iterable[BenchmarkResultRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table_from_rows(rows), path, compression="zstd")


def read_rows(path: Path) -> list[BenchmarkResultRow]:
    table = pq.read_table(path)
    validate_table(table)
    return [BenchmarkResultRow.from_record(record) for record in table.to_pylist()]
