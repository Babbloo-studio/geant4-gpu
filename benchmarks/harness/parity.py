#!/usr/bin/env python3
"""KS parity gate for G4GPU benchmark-harness observable Parquet files."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
from scipy.stats import ks_2samp

P_VALUE_MIN = 0.05

OBSERVABLE_ALIASES: dict[str, tuple[str, ...]] = {
    "edep_total": (
        "edep_total",
        "total_deposited_energy",
        "total_deposited_energy_mev",
    ),
    "step_count": ("step_count", "steps"),
    "secondary_multiplicity": (
        "secondary_multiplicity",
        "particle_multiplicity",
    ),
    "first_step_length": (
        "first_step_length",
        "first_step_length_mm",
        "firststepl",
    ),
    "neutron_capture_rate": ("neutron_capture_rate", "neutron_captures_per_event"),
}
REQUIRED_OBSERVABLES = tuple(name for name in OBSERVABLE_ALIASES if name != "neutron_capture_rate")
OPTIONAL_OBSERVABLES = ("neutron_capture_rate",)


@dataclass(frozen=True)
class ObservableKSResult:
    name: str
    vanilla_column: str
    opt_column: str
    statistic: float
    pvalue: float
    passed: bool

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ParityResult:
    passed: bool
    ks_stats: dict[str, float | None]
    failing_observables: list[str]
    observables: list[ObservableKSResult]
    skipped_observables: list[str]
    pvalue_min: float = P_VALUE_MIN

    def to_dict(self) -> dict[str, object]:
        return {
            "pass": self.passed,
            "ks_stats": self.ks_stats,
            "failing_observables": self.failing_observables,
            "observables": [observable.to_dict() for observable in self.observables],
            "skipped_observables": self.skipped_observables,
            "pvalue_min": self.pvalue_min,
        }


def _resolve_column(table: pa.Table, aliases: Iterable[str]) -> str | None:
    names = set(table.column_names)
    for alias in aliases:
        if alias in names:
            return alias
    return None


def _flatten_numeric_column(table: pa.Table, column: str, path: Path) -> np.ndarray:
    array = table[column].combine_chunks()
    if pa.types.is_list(array.type) or pa.types.is_large_list(array.type):
        array = pc.list_flatten(array)
    array = pc.drop_null(array)
    values = np.asarray(array.to_pylist(), dtype=float)
    values = values[np.isfinite(values)]
    if values.size == 0:
        raise ValueError(f"{path} column {column} has no finite values")
    return values


def _compare_observable(
    name: str,
    vanilla_table: pa.Table,
    opt_table: pa.Table,
    vanilla_path: Path,
    opt_path: Path,
    pvalue_min: float,
) -> ObservableKSResult:
    aliases = OBSERVABLE_ALIASES[name]
    vanilla_column = _resolve_column(vanilla_table, aliases)
    opt_column = _resolve_column(opt_table, aliases)
    if vanilla_column is None or opt_column is None:
        raise ValueError(
            f"missing required observable {name}: "
            f"vanilla_column={vanilla_column!r} opt_column={opt_column!r} aliases={aliases}"
        )
    vanilla_values = _flatten_numeric_column(vanilla_table, vanilla_column, vanilla_path)
    opt_values = _flatten_numeric_column(opt_table, opt_column, opt_path)
    ks = ks_2samp(vanilla_values, opt_values, alternative="two-sided", method="auto")
    pvalue = float(ks.pvalue)
    return ObservableKSResult(
        name=name,
        vanilla_column=vanilla_column,
        opt_column=opt_column,
        statistic=float(ks.statistic),
        pvalue=pvalue,
        passed=bool(pvalue > pvalue_min),
    )


def parity_gate(vanilla_parquet: str | Path, opt_parquet: str | Path, *, pvalue_min: float = P_VALUE_MIN) -> ParityResult:
    """Compare vanilla and optimized observable Parquet files with KS tests.

    All required observables must be present.  The neutron-capture observable is
    optional: if both files omit it, the gate records a skipped null p-value for
    non-W4 workloads; if either side contains it, both sides must contain it and
    it participates in the pass/fail decision.
    """

    if pvalue_min < 0.0 or pvalue_min > 1.0:
        raise ValueError("pvalue_min must be in [0, 1]")
    vanilla_path = Path(vanilla_parquet)
    opt_path = Path(opt_parquet)
    vanilla_table = pq.read_table(vanilla_path)
    opt_table = pq.read_table(opt_path)

    results: list[ObservableKSResult] = []
    skipped: list[str] = []
    for observable in REQUIRED_OBSERVABLES:
        results.append(
            _compare_observable(
                observable,
                vanilla_table,
                opt_table,
                vanilla_path,
                opt_path,
                pvalue_min,
            )
        )
    for observable in OPTIONAL_OBSERVABLES:
        aliases = OBSERVABLE_ALIASES[observable]
        vanilla_column = _resolve_column(vanilla_table, aliases)
        opt_column = _resolve_column(opt_table, aliases)
        if vanilla_column is None and opt_column is None:
            skipped.append(observable)
            continue
        results.append(
            _compare_observable(
                observable,
                vanilla_table,
                opt_table,
                vanilla_path,
                opt_path,
                pvalue_min,
            )
        )

    ks_stats: dict[str, float | None] = {result.name: result.pvalue for result in results}
    for observable in skipped:
        ks_stats[observable] = None
    failing = [f"{result.name}={result.pvalue:.6g}" for result in results if not result.passed]
    return ParityResult(
        passed=not failing,
        ks_stats=ks_stats,
        failing_observables=failing,
        observables=results,
        skipped_observables=skipped,
        pvalue_min=pvalue_min,
    )
