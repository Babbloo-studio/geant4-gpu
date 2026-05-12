#!/usr/bin/env python3
"""Fixture-only tests for future NNBAR W5/W6 adapter preflight checks."""

from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile

import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmarks.harness.builder import BuildError, resolve_workload  # noqa: E402
from benchmarks.harness.nnbar_preflight import (  # noqa: E402
    AdapterEvidence,
    REQUIRED_COLUMNS,
    check_adapter_preflight,
    check_w5_w6_preflight,
)


def _write_executable(path: Path) -> Path:
    path.write_text("#!/usr/bin/env bash\necho fixture-only\n", encoding="utf-8")
    path.chmod(path.stat().st_mode | 0o111)
    return path


def _write_macro(path: Path, label: str, *, seed_hook: bool = True, physics: bool = True) -> Path:
    text = [f"# {label}", f"# adapter {label}"]
    if physics:
        text.append("/physics_list FTFP_BERT")
    if seed_hook:
        text.append("/random/setSeeds {seed} {seed}")
    path.write_text("\n".join(text) + "\n", encoding="utf-8")
    return path


def _write_schema(path: Path, *, missing: str | None = None) -> Path:
    fields = []
    for name in sorted(REQUIRED_COLUMNS):
        if name == missing:
            continue
        if name == "event_name":
            fields.append(pa.field(name, pa.string()))
        else:
            fields.append(pa.field(name, pa.float64()))
    table = pa.Table.from_arrays([pa.array([], type=field.type) for field in fields], schema=pa.schema(fields))
    pq.write_table(table, path)
    return path


def _evidence(tmp: Path, workload: str, *, bad_count: bool = False, seed_hook: bool = True) -> AdapterEvidence:
    labels = {"W5": "nnbar_signal_full_event", "W6": "nnbar_cosmic_mu_full_event"}
    counts = {"W5": 1000, "W6": 500}
    exe = _write_executable(tmp / "nnbar-detector")
    macro = _write_macro(tmp / f"{workload}.mac", labels[workload], seed_hook=seed_hook)
    schema = _write_schema(tmp / f"{workload}.parquet")
    return AdapterEvidence(
        workload_id=workload,
        executable=exe,
        macro=macro,
        schema_sample=schema,
        n_events=counts[workload] + (1 if bad_count else 0),
        seeds=tuple(range(1001, 1021)),
        g4gpu_repo=ROOT,
    )


def test_fixture_preflight_can_pass_without_enabling_aliases(tmp_path: Path) -> None:
    report = check_adapter_preflight(_evidence(tmp_path, "W5"))
    assert report.ok, report.blockers
    try:
        resolve_workload("W5")
    except BuildError as exc:
        assert "methodology-blocked" in str(exc)
    else:
        raise AssertionError("W5 alias was enabled by fixture-only preflight")


def test_both_w5_w6_fixture_preflights_pass(tmp_path: Path) -> None:
    reports = check_w5_w6_preflight({"W5": _evidence(tmp_path, "W5"), "W6": _evidence(tmp_path, "W6")})
    assert [report.workload_id for report in reports] == ["W5", "W6"]
    assert all(report.ok for report in reports)


def test_preflight_reports_missing_fixture_evidence(tmp_path: Path) -> None:
    report = check_adapter_preflight(
        AdapterEvidence(
            workload_id="W5",
            executable=tmp_path / "missing-exe",
            macro=tmp_path / "missing.mac",
            schema_sample=tmp_path / "missing.parquet",
            n_events=999,
            seeds=(1001,),
            g4gpu_repo=ROOT,
        )
    )
    assert not report.ok
    joined = "\n".join(report.blockers)
    assert "NNBAR_EXECUTABLE" in joined
    assert "NNBAR_MACRO_W5" in joined
    assert "NNBAR_OUTPUT_SCHEMA_W5" in joined
    assert "NNBAR_EVENT_COUNT_W5" in joined
    assert "NNBAR_SEEDS" in joined


def test_preflight_rejects_bad_count_schema_and_seedless_macro(tmp_path: Path) -> None:
    evidence = _evidence(tmp_path, "W6", bad_count=True, seed_hook=False)
    bad_schema = _write_schema(tmp_path / "bad_schema.parquet", missing="per_step_time_ns")
    report = check_adapter_preflight(AdapterEvidence(**{**evidence.__dict__, "schema_sample": bad_schema}))
    assert not report.ok
    joined = "\n".join(report.blockers)
    assert "NNBAR_EVENT_COUNT_W6" in joined
    assert "per_step_time_ns" in joined
    assert "deterministic seed hook" in joined


def test_preflight_rejects_executable_inside_g4gpu_repo(tmp_path: Path) -> None:
    inside = ROOT / "build" / "fixture-nnbar-exe"
    _write_executable(inside)
    try:
        evidence = _evidence(tmp_path, "W5")
        report = check_adapter_preflight(AdapterEvidence(**{**evidence.__dict__, "executable": inside}))
        assert not report.ok
        assert any("outside the G4GPU repo" in blocker for blocker in report.blockers)
    finally:
        inside.unlink(missing_ok=True)


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        test_fixture_preflight_can_pass_without_enabling_aliases(tmp)
        test_both_w5_w6_fixture_preflights_pass(tmp)
        test_preflight_reports_missing_fixture_evidence(tmp)
        test_preflight_rejects_bad_count_schema_and_seedless_macro(tmp)
        test_preflight_rejects_executable_inside_g4gpu_repo(tmp)
    print("benchmark_harness_nnbar_preflight: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
