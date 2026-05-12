#!/usr/bin/env python3
"""Fail-closed sampler-observable KS gates for targeted Geant4 optimizations.

BD-geant4-001 changes the Moller/Bhabha delta-ray sampler in Geant4 source, so
an event-level parity gate alone is not enough.  This module defines the
minimum distribution-level observables that must be present before any BD-001
speedup row can be trusted.  It performs no event execution and writes no
benchmark result rows.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Mapping

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
from scipy.stats import ks_2samp

from .parity import P_VALUE_MIN

BD001_OBSERVABLE_ALIASES: Mapping[str, tuple[str, ...]] = {
    "sampler_x": (
        "bd001_sampler_x",
        "sampler_x",
        "moller_bhabha_x",
        "delta_ray_sampler_x",
    ),
    "delta_ray_ke_mev": (
        "bd001_delta_ray_ke_mev",
        "delta_ray_ke_mev",
        "delta_electron_ke_mev",
        "secondary_kinetic_energy_mev",
    ),
    "delta_ray_theta_rad": (
        "bd001_delta_ray_theta_rad",
        "delta_ray_theta_rad",
        "delta_electron_theta_rad",
        "secondary_theta_rad",
    ),
    "downstream_dedx_mev_mm": (
        "bd001_downstream_dedx_mev_mm",
        "downstream_dedx_mev_mm",
        "dedx_mev_mm",
        "energy_loss_per_mm",
    ),
}
BD001_REQUIRED_OBSERVABLES = tuple(BD001_OBSERVABLE_ALIASES)


class SamplerObservableError(ValueError):
    """Raised when sampler-observable evidence is absent or malformed."""


@dataclass(frozen=True)
class SamplerObservableKSResult:
    name: str
    vanilla_column: str
    opt_column: str
    statistic: float
    pvalue: float
    passed: bool

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class SamplerObservableGateResult:
    opt_id: str
    passed: bool
    ks_stats: dict[str, float]
    failing_observables: list[str]
    observables: list[SamplerObservableKSResult]
    pvalue_min: float = P_VALUE_MIN

    def to_dict(self) -> dict[str, object]:
        return {
            "opt_id": self.opt_id,
            "pass": self.passed,
            "ks_stats": self.ks_stats,
            "failing_observables": self.failing_observables,
            "observables": [observable.to_dict() for observable in self.observables],
            "pvalue_min": self.pvalue_min,
        }


def bd001_sampler_observable_gate(
    vanilla_parquet: str | Path,
    opt_parquet: str | Path,
    *,
    pvalue_min: float = P_VALUE_MIN,
) -> SamplerObservableGateResult:
    """KS-test the BD-geant4-001 sampler-specific observable contract.

    Required observables are sampled ``x``, delta-ray kinetic energy, delta-ray
    angle, and downstream dE/dx.  Missing columns, empty/null-only columns, and
    non-finite values are all fail-closed errors rather than skipped checks.
    """

    if pvalue_min < 0.0 or pvalue_min > 1.0:
        raise SamplerObservableError("pvalue_min must be in [0, 1]")
    vanilla_path = Path(vanilla_parquet)
    opt_path = Path(opt_parquet)
    vanilla_table = pq.read_table(vanilla_path)
    opt_table = pq.read_table(opt_path)

    results = [
        _compare_observable(name, vanilla_table, opt_table, vanilla_path, opt_path, pvalue_min)
        for name in BD001_REQUIRED_OBSERVABLES
    ]
    failing = [f"{result.name}={result.pvalue:.6g}" for result in results if not result.passed]
    return SamplerObservableGateResult(
        opt_id="BD-geant4-001",
        passed=not failing,
        ks_stats={result.name: result.pvalue for result in results},
        failing_observables=failing,
        observables=results,
        pvalue_min=pvalue_min,
    )


def _compare_observable(
    name: str,
    vanilla_table: pa.Table,
    opt_table: pa.Table,
    vanilla_path: Path,
    opt_path: Path,
    pvalue_min: float,
) -> SamplerObservableKSResult:
    aliases = BD001_OBSERVABLE_ALIASES[name]
    vanilla_column = _resolve_column(vanilla_table, aliases)
    opt_column = _resolve_column(opt_table, aliases)
    if vanilla_column is None or opt_column is None:
        raise SamplerObservableError(
            f"BD-geant4-001 missing required sampler observable {name}: "
            f"vanilla_column={vanilla_column!r} opt_column={opt_column!r} aliases={aliases}"
        )
    vanilla_values = _flatten_numeric_column(vanilla_table, vanilla_column, vanilla_path)
    opt_values = _flatten_numeric_column(opt_table, opt_column, opt_path)
    ks = ks_2samp(vanilla_values, opt_values, alternative="two-sided", method="auto")
    pvalue = float(ks.pvalue)
    return SamplerObservableKSResult(
        name=name,
        vanilla_column=vanilla_column,
        opt_column=opt_column,
        statistic=float(ks.statistic),
        pvalue=pvalue,
        passed=bool(pvalue > pvalue_min),
    )


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
    if not pa.types.is_integer(array.type) and not pa.types.is_floating(array.type):
        raise SamplerObservableError(f"{path} column {column} must be numeric, got {array.type}")
    values = np.asarray(pc.drop_null(array).to_pylist(), dtype=float)
    if values.size == 0:
        raise SamplerObservableError(f"{path} column {column} has no finite values")
    if not np.all(np.isfinite(values)):
        raise SamplerObservableError(f"{path} column {column} contains non-finite values")
    return values
