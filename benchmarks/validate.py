#!/usr/bin/env python3
"""Statistical comparison gate for phase-5 benchmark Parquet outputs.

The validator is intentionally small and file-format focused: it consumes two
benchmark Parquet files, compares the four phase-5 gate observables, and exits
nonzero if either a KS test or binned KL-divergence check fails.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pyarrow.parquet as pq
from scipy.stats import ks_2samp


SCALAR_OBSERVABLES = {
    "total_deposited_energy": "total_deposited_energy_mev",
    "leading_particle_ke": "leading_particle_ke_mev",
    "particle_multiplicity": "particle_multiplicity",
}
VERTEX_COLUMNS = ("vertex_x_mm", "vertex_y_mm", "vertex_z_mm")
REQUIRED_COLUMNS = tuple(SCALAR_OBSERVABLES.values()) + VERTEX_COLUMNS


@dataclass
class ObservableResult:
    name: str
    ks_statistic: float
    ks_pvalue: float
    kl_divergence: float
    pass_ks: bool
    pass_kl: bool

    @property
    def passed(self) -> bool:
        return self.pass_ks and self.pass_kl


@dataclass
class ValidationSummary:
    reference: str
    candidate: str
    ks_pvalue_min: float
    kl_tolerance: float
    rows_reference: int
    rows_candidate: int
    observables: list[ObservableResult]

    @property
    def passed(self) -> bool:
        return all(result.passed for result in self.observables)

    def to_json_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["passed"] = self.passed
        for item, result in zip(payload["observables"], self.observables):
            item["passed"] = result.passed
        return payload


def _read_columns(path: Path) -> dict[str, np.ndarray]:
    table = pq.read_table(path)
    missing = sorted(set(REQUIRED_COLUMNS) - set(table.column_names))
    if missing:
        raise ValueError(f"{path} is missing required columns: {missing}")
    data: dict[str, np.ndarray] = {}
    for column in REQUIRED_COLUMNS:
        values = table[column].to_numpy(zero_copy_only=False)
        if values.size == 0:
            raise ValueError(f"{path} column {column} is empty")
        data[column] = values.astype(float)
    return data


def _vertex_radius(data: dict[str, np.ndarray]) -> np.ndarray:
    x, y, z = (data[column] for column in VERTEX_COLUMNS)
    return np.sqrt(x * x + y * y + z * z)


def _finite_pair(reference: np.ndarray, candidate: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    reference = reference[np.isfinite(reference)]
    candidate = candidate[np.isfinite(candidate)]
    if reference.size == 0 or candidate.size == 0:
        raise ValueError("observable has no finite values in one side of the comparison")
    return reference, candidate


def _histogram_edges(reference: np.ndarray, candidate: np.ndarray, bins: int) -> np.ndarray:
    combined = np.concatenate([reference, candidate])
    lo = float(np.min(combined))
    hi = float(np.max(combined))
    if math.isclose(lo, hi):
        delta = max(1.0, abs(lo) * 1.0e-6)
        return np.array([lo - delta, hi + delta], dtype=float)
    return np.linspace(lo, hi, bins + 1)


def _kl_divergence(reference: np.ndarray, candidate: np.ndarray, bins: int) -> float:
    edges = _histogram_edges(reference, candidate, bins)
    ref_counts, _ = np.histogram(reference, bins=edges)
    cand_counts, _ = np.histogram(candidate, bins=edges)
    epsilon = 1.0e-12
    ref_pdf = ref_counts.astype(float) + epsilon
    cand_pdf = cand_counts.astype(float) + epsilon
    ref_pdf /= np.sum(ref_pdf)
    cand_pdf /= np.sum(cand_pdf)
    return float(np.sum(ref_pdf * np.log(ref_pdf / cand_pdf)))


def _compare_observable(
    name: str,
    reference: np.ndarray,
    candidate: np.ndarray,
    *,
    bins: int,
    ks_pvalue_min: float,
    kl_tolerance: float,
) -> ObservableResult:
    reference, candidate = _finite_pair(reference, candidate)
    ks = ks_2samp(reference, candidate, alternative="two-sided", method="auto")
    kl = _kl_divergence(reference, candidate, bins)
    return ObservableResult(
        name=name,
        ks_statistic=float(ks.statistic),
        ks_pvalue=float(ks.pvalue),
        kl_divergence=kl,
        pass_ks=bool(ks.pvalue >= ks_pvalue_min),
        pass_kl=bool(kl <= kl_tolerance),
    )


def compare_files(
    reference_path: Path,
    candidate_path: Path,
    *,
    bins: int = 50,
    ks_pvalue_min: float = 0.05,
    kl_tolerance: float = 0.01,
) -> ValidationSummary:
    reference = _read_columns(reference_path)
    candidate = _read_columns(candidate_path)
    observables: list[ObservableResult] = []
    for name, column in SCALAR_OBSERVABLES.items():
        observables.append(
            _compare_observable(
                name,
                reference[column],
                candidate[column],
                bins=bins,
                ks_pvalue_min=ks_pvalue_min,
                kl_tolerance=kl_tolerance,
            )
        )
    observables.append(
        _compare_observable(
            "vertex_position_radius",
            _vertex_radius(reference),
            _vertex_radius(candidate),
            bins=bins,
            ks_pvalue_min=ks_pvalue_min,
            kl_tolerance=kl_tolerance,
        )
    )
    return ValidationSummary(
        reference=str(reference_path),
        candidate=str(candidate_path),
        ks_pvalue_min=ks_pvalue_min,
        kl_tolerance=kl_tolerance,
        rows_reference=len(next(iter(reference.values()))),
        rows_candidate=len(next(iter(candidate.values()))),
        observables=observables,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reference", type=Path, help="reference Geant4-baseline Parquet")
    parser.add_argument("candidate", type=Path, help="candidate Parquet to compare")
    parser.add_argument("--bins", type=int, default=50, help="histogram bins for KL checks")
    parser.add_argument(
        "--ks-pvalue-min",
        type=float,
        default=0.05,
        help="minimum two-sample KS p-value",
    )
    parser.add_argument(
        "--kl-tolerance",
        type=float,
        default=0.01,
        help="maximum binned KL divergence per observable",
    )
    parser.add_argument("--json", type=Path, help="optional JSON summary output path")
    return parser


def _print_table(results: Iterable[ObservableResult]) -> None:
    print("observable,ks_statistic,ks_pvalue,kl_divergence,status")
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        print(
            f"{result.name},{result.ks_statistic:.8g},{result.ks_pvalue:.8g},"
            f"{result.kl_divergence:.8g},{status}"
        )


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.bins <= 0:
        raise SystemExit("--bins must be positive")
    summary = compare_files(
        args.reference,
        args.candidate,
        bins=args.bins,
        ks_pvalue_min=args.ks_pvalue_min,
        kl_tolerance=args.kl_tolerance,
    )
    _print_table(summary.observables)
    payload = summary.to_json_dict()
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    else:
        print(json.dumps(payload, sort_keys=True))
    return 0 if summary.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
