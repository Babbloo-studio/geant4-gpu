#!/usr/bin/env python3
"""V7 full-event validation runner skeleton.

The comparison and JSON-summary machinery is present, but ROOT/Parquet readers
are intentionally stubbed until the next compact unit maps real event branches.
See docs/VALIDATION.md, section "V7: Full event validation (end-to-end)".
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

TEST_NAME = "V7"
KS_THRESHOLD = 0.05
MEAN_SIGMA_LIMIT = 1.0
RMS_SIGMA_LIMIT = 2.0
SPEC_REF = 'docs/VALIDATION.md "V7: Full event validation (end-to-end)"'


@dataclass(frozen=True)
class ObservableSample:
    """One candidate/reference distribution pair to compare."""

    subdetector: str
    observable: str
    candidate: tuple[float, ...]
    reference: tuple[float, ...]
    layer: str | None = None
    candidate_y: tuple[float, ...] | None = None
    reference_y: tuple[float, ...] | None = None

    @property
    def label(self) -> str:
        base = f"{self.subdetector}.{self.observable}"
        if self.layer is not None:
            return f"{base}.layer_{self.layer}"
        return base


@dataclass(frozen=True)
class ComparisonResult:
    """Serializable V7 comparison row."""

    test: str
    observable: str
    status: str
    ks_pvalue: float
    mean_delta: float
    rms_delta: float
    mean_sigma: float
    rms_sigma: float
    n_candidate: int
    n_reference: int
    failure_reasons: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "test": self.test,
            "observable": self.observable,
            "status": self.status,
            "ks_pvalue": self.ks_pvalue,
            "mean_delta": self.mean_delta,
            "rms_delta": self.rms_delta,
            "mean_sigma": self.mean_sigma,
            "rms_sigma": self.rms_sigma,
            "n_candidate": self.n_candidate,
            "n_reference": self.n_reference,
            "failure_reasons": list(self.failure_reasons),
        }


def finite_values(values: Iterable[float]) -> tuple[float, ...]:
    """Return finite floats only, preserving order."""

    return tuple(float(value) for value in values if math.isfinite(float(value)))


def mean(values: Sequence[float]) -> float:
    return sum(values) / len(values)


def sample_rms(values: Sequence[float]) -> float:
    center = mean(values)
    return math.sqrt(sum((value - center) ** 2 for value in values) / len(values))


def standard_error(values: Sequence[float]) -> float:
    if len(values) < 2:
        return math.inf
    return sample_rms(values) / math.sqrt(len(values))


def rms_standard_error(values: Sequence[float]) -> float:
    if len(values) < 2:
        return math.inf
    return sample_rms(values) / math.sqrt(2.0 * (len(values) - 1))


def combined_uncertainty(left: float, right: float) -> float:
    return math.sqrt(left * left + right * right)


def ks_1d(candidate: Sequence[float], reference: Sequence[float]) -> float:
    """Run scipy's two-sample KS test lazily."""

    try:
        from scipy.stats import ks_2samp
    except ImportError as exc:  # pragma: no cover - depends on runtime env
        raise RuntimeError("scipy is required for V7 KS comparisons") from exc
    return float(ks_2samp(candidate, reference).pvalue)


def ks_xy(
    sample: ObservableSample,
    candidate_x: Sequence[float],
    reference_x: Sequence[float],
) -> float:
    """Conservative x-y comparison: require both projected KS tests to pass."""

    if sample.candidate_y is None or sample.reference_y is None:
        return ks_1d(candidate_x, reference_x)
    candidate_y = finite_values(sample.candidate_y)
    reference_y = finite_values(sample.reference_y)
    if len(candidate_y) < 2 or len(reference_y) < 2:
        return 0.0
    px = ks_1d(candidate_x, reference_x)
    py = ks_1d(candidate_y, reference_y)
    return min(px, py)


def compare_sample(sample: ObservableSample) -> ComparisonResult:
    candidate = finite_values(sample.candidate)
    reference = finite_values(sample.reference)
    failures: list[str] = []

    if len(candidate) < 2:
        failures.append("candidate_too_small")
    if len(reference) < 2:
        failures.append("reference_too_small")

    if failures:
        return ComparisonResult(
            test=TEST_NAME,
            observable=sample.label,
            status="FAIL",
            ks_pvalue=0.0,
            mean_delta=math.nan,
            rms_delta=math.nan,
            mean_sigma=math.inf,
            rms_sigma=math.inf,
            n_candidate=len(candidate),
            n_reference=len(reference),
            failure_reasons=tuple(failures),
        )

    ks_pvalue = ks_xy(sample, candidate, reference)
    mean_delta = mean(candidate) - mean(reference)
    rms_delta = sample_rms(candidate) - sample_rms(reference)
    mean_sigma = combined_uncertainty(standard_error(candidate), standard_error(reference))
    rms_sigma = combined_uncertainty(rms_standard_error(candidate), rms_standard_error(reference))

    if ks_pvalue <= KS_THRESHOLD:
        failures.append("ks_pvalue_below_0p05")
    if abs(mean_delta) > MEAN_SIGMA_LIMIT * mean_sigma:
        failures.append("mean_delta_exceeds_1sigma")
    if abs(rms_delta) > RMS_SIGMA_LIMIT * rms_sigma:
        failures.append("rms_delta_exceeds_2sigma")

    return ComparisonResult(
        test=TEST_NAME,
        observable=sample.label,
        status="PASS" if not failures else "FAIL",
        ks_pvalue=ks_pvalue,
        mean_delta=mean_delta,
        rms_delta=rms_delta,
        mean_sigma=mean_sigma,
        rms_sigma=rms_sigma,
        n_candidate=len(candidate),
        n_reference=len(reference),
        failure_reasons=tuple(failures),
    )


def compare_observables(samples: Iterable[ObservableSample]) -> list[ComparisonResult]:
    return [compare_sample(sample) for sample in samples]


def load_observables(candidate: Path, reference: Path) -> list[ObservableSample]:
    """Load event-level observable samples from ROOT or Parquet inputs.

    The real branch mapping is deliberately not implemented in this compact
    scaffold.  Keeping the NotImplementedError here lets the gated shakedown
    prove Python/module/SLURM wiring without making a physics claim.
    """

    candidate_suffix = candidate.suffix.lower()
    reference_suffix = reference.suffix.lower()
    supported = {".root", ".parquet"}
    if candidate_suffix not in supported:
        raise ValueError(f"unsupported candidate format: {candidate}")
    if reference_suffix not in supported:
        raise ValueError(f"unsupported reference format: {reference}")
    if candidate_suffix != reference_suffix:
        raise ValueError("candidate and reference formats must match in the scaffold")

    if candidate_suffix == ".root":
        return load_root_observables(candidate, reference)
    return load_parquet_observables(candidate, reference)


def load_root_observables(candidate: Path, reference: Path) -> list[ObservableSample]:
    """Future ROOT reader hook using ``uproot``.

    The branch names and histogram ownership are intentionally not guessed in
    this scaffold.  A later implementation should import uproot lazily here and
    map event records into ObservableSample groups.
    """

    raise NotImplementedError(
        "V7 ROOT event reader is scaffold-only; implement uproot branch "
        f"mapping for {candidate} and {reference} before physics use per {SPEC_REF}"
    )


def load_parquet_observables(candidate: Path, reference: Path) -> list[ObservableSample]:
    """Future Parquet reader hook using ``pyarrow``.

    The schema-to-observable contract is deliberately fail-closed until real
    event files are available.  A later implementation should import pyarrow
    lazily here and map columns into ObservableSample groups.
    """

    raise NotImplementedError(
        "V7 ROOT/Parquet event readers are scaffold-only; implement branch "
        f"mapping for {candidate} and {reference} before physics use per {SPEC_REF}"
    )


def write_summary(results: Sequence[ComparisonResult], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "test": TEST_NAME,
        "status": "PASS" if all(result.status == "PASS" for result in results) else "FAIL",
        "results": [result.as_dict() for result in results],
    }
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def resolve_run_path(path: Path, run_root: Path) -> Path:
    """Resolve relative scaffold paths below a writable V7 run root."""

    expanded = path.expanduser()
    if expanded.is_absolute():
        return expanded
    return run_root / expanded


def run(candidate: Path, reference: Path, output: Path, run_root: Path) -> int:
    run_root = run_root.expanduser().resolve()
    candidate = resolve_run_path(candidate, run_root)
    reference = resolve_run_path(reference, run_root)
    output = resolve_run_path(output, run_root)
    print(f"V7 run root: {run_root}", file=sys.stderr)
    print(f"V7 candidate input: {candidate}", file=sys.stderr)
    print(f"V7 reference input: {reference}", file=sys.stderr)
    print(f"V7 summary output: {output}", file=sys.stderr)
    samples = load_observables(candidate, reference)
    results = compare_observables(samples)
    write_summary(results, output)
    return 0 if all(result.status == "PASS" for result in results) else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", required=True, type=Path, help="G4GPU ROOT/Parquet output")
    parser.add_argument("--reference", required=True, type=Path, help="Geant4 reference ROOT/Parquet output")
    parser.add_argument(
        "--run-root",
        default=Path(os.environ.get("G4GPU_V7_RUN_ROOT", ".")),
        type=Path,
        help=(
            "Writable root for relative input/output paths "
            "(default: G4GPU_V7_RUN_ROOT or current directory)"
        ),
    )
    parser.add_argument(
        "--output",
        default=Path("output/v7_summary.json"),
        type=Path,
        help="JSON summary path (default: output/v7_summary.json)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return run(args.candidate, args.reference, args.output, args.run_root)


if __name__ == "__main__":
    raise SystemExit(main())
