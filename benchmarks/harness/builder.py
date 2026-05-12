#!/usr/bin/env python3
"""Fail-closed CMake builder for the benchmark harness.

The runner is responsible for SLURM submission and execution.  This module only
configures and builds a requested workload, records the exact CMake transcript,
and refuses to return if the transcript contains an error marker or the expected
binary is absent.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
from typing import Mapping, Sequence

DEFAULT_GEANT4_PREFIX = Path("/projects/hep/fs10/shared/nnbar/billy/packages/hibeam_env")
DEFAULT_GEANT4_SOURCE = Path("/projects/hep/fs10/shared/nnbar/billy/geant4-fork")
DEFAULT_PYTHON = DEFAULT_GEANT4_PREFIX / "bin/python"
REPO_ROOT = Path(__file__).resolve().parents[2]
ERROR_TOKEN = re.compile(r"(^|[^A-Za-z])Error([^A-Za-z]|$)")


class BuildError(RuntimeError):
    """Raised when configure/build evidence is missing or fail-closed."""


@dataclass(frozen=True)
class WorkloadSpec:
    workload_id: str
    source_rel: str | None
    target: str
    binary_rel: str
    local_repo_source: bool = False


WORKLOADS: dict[str, WorkloadSpec] = {
    # Canonical Phase-5 publication workloads.  W1--W6 remain the stable
    # harness IDs.  W5/W6 are intentionally absent here until true NNBAR
    # full-event drivers exist; see METHODOLOGY_BLOCKERS below.
    "W1": WorkloadSpec("W1", None, "benchmark_gamma_100mev", "benchmarks/benchmark_gamma_100mev", True),
    "W2": WorkloadSpec("W2", None, "benchmark_muon_10gev", "benchmarks/benchmark_muon_10gev", True),
    "W3": WorkloadSpec("W3", None, "benchmark_nbar_carbon", "benchmarks/benchmark_nbar_carbon", True),
    "W4": WorkloadSpec("W4", None, "benchmark_cosmic_shower", "benchmarks/benchmark_cosmic_shower", True),
    # Stand-in event drivers remain addressable only by their event names so
    # they cannot be mistaken for paper-methodology W5/W6 rows.
    "optical_scintillator": WorkloadSpec(
        "optical_scintillator",
        None,
        "benchmark_optical_scintillator",
        "benchmarks/benchmark_optical_scintillator",
        True,
    ),
    "beam_neutron": WorkloadSpec(
        "beam_neutron", None, "benchmark_beam_neutron", "benchmarks/benchmark_beam_neutron", True
    ),
}
ALIASES = {
    "gamma_100mev": "W1",
    "muon_10gev": "W2",
    "nbar_carbon": "W3",
    "cosmic_shower": "W4",
}
METHODOLOGY_BLOCKERS = {
    "W5": (
        "W5 is methodology-blocked: docs/specs/paper-methodology.md defines "
        "W5 as the NNBAR full event (signal), 1000 events, FTFP_BERT. "
        "This checkout only has the stand-in event driver "
        "'optical_scintillator', which is not a paper-ready W5 driver. See docs/specs/w5_w6_full_event_drivers.md."
    ),
    "W6": (
        "W6 is methodology-blocked: docs/specs/paper-methodology.md defines "
        "W6 as the NNBAR full event (cosmic mu), 500 events, FTFP_BERT. "
        "This checkout only has the stand-in event driver 'beam_neutron', "
        "which is not a paper-ready W6 driver. See docs/specs/w5_w6_full_event_drivers.md."
    ),
}


def build_vanilla(
    geant4_prefix: str | Path,
    workload: str,
    output_dir: str | Path,
    *,
    geant4_source: str | Path = DEFAULT_GEANT4_SOURCE,
    source_dir: str | Path | None = None,
    log_dir: str | Path | None = None,
    opt_id: str = "vanilla",
    hw_id: str = "unknown",
    cmake: str | Path = "cmake",
    jobs: int = 2,
    clean: bool = True,
    dry_run: bool = False,
    env: Mapping[str, str] | None = None,
) -> Path:
    """Configure and build the vanilla workload, returning the build path."""

    return _build(
        variant="vanilla",
        geant4_prefix=geant4_prefix,
        workload=workload,
        output_dir=output_dir,
        geant4_source=geant4_source,
        source_dir=source_dir,
        log_dir=log_dir,
        opt_id=opt_id,
        hw_id=hw_id,
        cmake=cmake,
        jobs=jobs,
        clean=clean,
        dry_run=dry_run,
        env=env,
        cmake_flags=(),
    )


def build_optimized(
    geant4_prefix: str | Path,
    opt_branch: str,
    cmake_flags: str | Sequence[str],
    workload: str,
    output_dir: str | Path,
    *,
    geant4_source: str | Path = DEFAULT_GEANT4_SOURCE,
    source_dir: str | Path | None = None,
    log_dir: str | Path | None = None,
    opt_id: str | None = None,
    hw_id: str = "unknown",
    cmake: str | Path = "cmake",
    jobs: int = 2,
    clean: bool = True,
    dry_run: bool = False,
    env: Mapping[str, str] | None = None,
    verify_ref: bool = True,
) -> Path:
    """Configure and build the optimized workload, returning the build path.

    ``verify_ref`` defaults to fail-closed: the source tree must already be at
    ``opt_branch`` or the matching commit.  The builder deliberately does not
    checkout branches or submit jobs.
    """

    flags = shlex.split(cmake_flags) if isinstance(cmake_flags, str) else tuple(cmake_flags)
    source = _source_path(workload, geant4_source, source_dir)
    if verify_ref and not dry_run:
        _verify_source_ref(source, opt_branch)
    return _build(
        variant="optimized",
        geant4_prefix=geant4_prefix,
        workload=workload,
        output_dir=output_dir,
        geant4_source=geant4_source,
        source_dir=source,
        log_dir=log_dir,
        opt_id=opt_id or _sanitize(opt_branch),
        hw_id=hw_id,
        cmake=cmake,
        jobs=jobs,
        clean=clean,
        dry_run=dry_run,
        env=env,
        cmake_flags=flags,
    )


def resolve_workload(workload: str) -> WorkloadSpec:
    key = str(workload).strip()
    blocker = METHODOLOGY_BLOCKERS.get(key.upper())
    if blocker is not None:
        raise BuildError(blocker)
    canonical = WORKLOADS.get(key) or WORKLOADS.get(ALIASES.get(key.lower(), ""))
    if canonical is not None:
        return canonical
    if key.startswith("benchmark_"):
        return WorkloadSpec(key, None, key, f"benchmarks/{key}", True)
    raise BuildError(
        f"unknown benchmark workload {workload!r}; expected W1-W4, an explicit phase-5 stand-in "
        "event name, or benchmark_*; W5/W6 are blocked until true NNBAR full-event drivers exist"
    )


def _build(
    *,
    variant: str,
    geant4_prefix: str | Path,
    workload: str,
    output_dir: str | Path,
    geant4_source: str | Path,
    source_dir: str | Path | None,
    log_dir: str | Path | None,
    opt_id: str,
    hw_id: str,
    cmake: str | Path,
    jobs: int,
    clean: bool,
    dry_run: bool,
    env: Mapping[str, str] | None,
    cmake_flags: Sequence[str],
) -> Path:
    spec = resolve_workload(workload)
    prefix = Path(geant4_prefix)
    geant4_dir = _geant4_dir(prefix)
    source = Path(source_dir) if source_dir is not None else _source_path(workload, geant4_source, None)
    if not source.exists():
        raise BuildError(f"workload source directory is absent: {source}")
    if not dry_run and not geant4_dir.exists():
        raise BuildError(f"Geant4 CMake config directory is absent: {geant4_dir}")
    build_dir = Path(output_dir) / f"{variant}_{_sanitize(opt_id)}_{_sanitize(spec.workload_id)}"
    log_root = Path(log_dir) if log_dir is not None else REPO_ROOT / "benchmarks/build_logs"
    log_path = log_root / f"{_sanitize(opt_id)}_{_sanitize(hw_id)}.txt"
    build_env = _build_env(prefix, env)
    configure = _configure_command(spec, cmake, source, build_dir, geant4_dir, prefix, cmake_flags)
    build = [str(cmake), "--build", str(build_dir), "--target", spec.target, "-j", str(jobs)]

    log_root.mkdir(parents=True, exist_ok=True)
    if clean and build_dir.exists() and not dry_run:
        shutil.rmtree(build_dir)
    build_dir.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as handle:
        _write_header(handle, spec, source, build_dir, prefix, geant4_dir, dry_run, (configure, build))
        if dry_run:
            handle.write("\nDRY-RUN: configure/build commands were not executed.\n")
            return build_dir
        for command in (configure, build):
            _run_logged(command, handle, build_env)

    _assert_log_clean(log_path)
    _assert_binary_present(build_dir, spec, log_path)
    return build_dir


def _source_path(workload: str, geant4_source: str | Path, source_dir: str | Path | None) -> Path:
    if source_dir is not None:
        return Path(source_dir)
    spec = resolve_workload(workload)
    if spec.local_repo_source:
        return REPO_ROOT
    if spec.source_rel is None:
        raise BuildError(f"workload {workload!r} has no source directory mapping")
    return Path(geant4_source) / spec.source_rel


def _geant4_dir(prefix_or_dir: Path) -> Path:
    if prefix_or_dir.name == "Geant4" or (prefix_or_dir / "Geant4Config.cmake").exists():
        return prefix_or_dir
    return prefix_or_dir / "lib/cmake/Geant4"


def _configure_command(
    spec: WorkloadSpec,
    cmake: str | Path,
    source: Path,
    build_dir: Path,
    geant4_dir: Path,
    prefix: Path,
    cmake_flags: Sequence[str],
) -> list[str]:
    command = [
        str(cmake),
        "-S",
        str(source),
        "-B",
        str(build_dir),
        f"-DGeant4_DIR={geant4_dir}",
        f"-DCMAKE_PREFIX_PATH={prefix};{prefix / 'lib/CLHEP-2.4.6.2'}",
        f"-DZLIB_ROOT={prefix}",
        f"-DZLIB_LIBRARY={prefix / 'lib/libz.so'}",
        f"-DZLIB_INCLUDE_DIR={prefix / 'include'}",
        "-DWITH_GEANT4_UIVIS=OFF",
    ]
    if spec.local_repo_source:
        command.extend(
            [
                "-DCMAKE_CUDA_COMPILER=nvcc",
                "-DG4GPU_WITH_OPTICAL=OFF",
                "-DG4GPU_WITH_RTX=OFF",
                f"-DG4GPU_BENCHMARK_PYTHON={DEFAULT_PYTHON}",
            ]
        )
    command.extend(str(flag) for flag in cmake_flags)
    return command


def _build_env(prefix: Path, extra: Mapping[str, str] | None) -> dict[str, str]:
    env = dict(os.environ)
    if extra:
        env.update({str(key): str(value) for key, value in extra.items()})
    env["GEANT4_PREFIX"] = str(prefix)
    env["CMAKE_PREFIX_PATH"] = _prepend_env(env.get("CMAKE_PREFIX_PATH"), (prefix, prefix / "lib/CLHEP-2.4.6.2"))
    env["LD_LIBRARY_PATH"] = _prepend_env(env.get("LD_LIBRARY_PATH"), (prefix / "lib",))
    data = prefix / "share/Geant4/data"
    for name, rel in {
        "G4NEUTRONHPDATA": "NDL4.7.1",
        "G4LEDATA": "EMLOW8.5",
        "G4LEVELGAMMADATA": "PhotonEvaporation5.7",
        "G4RADIOACTIVEDATA": "RadioactiveDecay5.6",
        "G4PARTICLEXSDATA": "PARTICLEXS4.0",
        "G4PIIDATA": "PII1.3",
        "G4REALSURFACEDATA": "RealSurface2.2",
        "G4SAIDXSDATA": "SAIDDATA2.0",
        "G4ABLADATA": "ABLA3.3",
        "G4INCLDATA": "INCL1.2",
        "G4ENSDFSTATEDATA": "ENSDFSTATE2.3",
    }.items():
        env.setdefault(name, str(data / rel))
    return env


def _prepend_env(current: str | None, paths: Sequence[Path]) -> str:
    prefix = [str(path) for path in paths]
    if current:
        prefix.append(current)
    return os.pathsep.join(prefix)


def _run_logged(command: Sequence[str], handle, env: Mapping[str, str]) -> None:
    handle.write("\n$ " + shlex.join([str(part) for part in command]) + "\n")
    handle.flush()
    proc = subprocess.run(
        [str(part) for part in command],
        env=dict(env),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    handle.write(proc.stdout)
    if proc.returncode != 0:
        raise BuildError(f"command failed with rc={proc.returncode}: {shlex.join(command)}")


def _assert_log_clean(log_path: Path) -> None:
    text = log_path.read_text(encoding="utf-8", errors="replace")
    for lineno, line in enumerate(text.splitlines(), start=1):
        if ERROR_TOKEN.search(line):
            raise BuildError(f"build log contains Error at {log_path}:{lineno}: {line}")


def _assert_binary_present(build_dir: Path, spec: WorkloadSpec, log_path: Path) -> None:
    candidates = [
        build_dir / spec.binary_rel,
        build_dir / spec.target,
        build_dir / "benchmarks" / spec.target,
        build_dir / "tests" / spec.target,
    ]
    if not any(path.is_file() for path in candidates):
        expected = ", ".join(str(path) for path in candidates)
        raise BuildError(f"expected benchmark binary is absent after build; checked {expected}; log={log_path}")


def _verify_source_ref(source: Path, opt_branch: str) -> None:
    if not (source / ".git").exists():
        raise BuildError(f"cannot verify opt_branch={opt_branch!r}: {source} is not a git worktree")
    head = _git(source, "rev-parse", "HEAD")
    try:
        target = _git(source, "rev-parse", f"{opt_branch}^{{commit}}")
    except BuildError as exc:
        raise BuildError(f"cannot resolve opt_branch={opt_branch!r} in {source}") from exc
    if head != target:
        branch = _git(source, "rev-parse", "--abbrev-ref", "HEAD")
        raise BuildError(f"source tree is at {branch}/{head[:12]}, not requested {opt_branch}/{target[:12]}")


def _git(source: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(source), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise BuildError(proc.stdout.strip())
    return proc.stdout.strip()


def _sanitize(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", str(value)).strip("-") or "unknown"


def _write_header(
    handle,
    spec: WorkloadSpec,
    source: Path,
    build_dir: Path,
    prefix: Path,
    geant4_dir: Path,
    dry_run: bool,
    commands: Sequence[Sequence[str]],
) -> None:
    handle.write("# G4GPU benchmark harness build log\n")
    handle.write(f"workload={spec.workload_id}\n")
    handle.write(f"target={spec.target}\n")
    handle.write(f"source={source}\n")
    handle.write(f"build_dir={build_dir}\n")
    handle.write(f"geant4_prefix={prefix}\n")
    handle.write(f"geant4_dir={geant4_dir}\n")
    handle.write(f"dry_run={dry_run}\n")
    for command in commands:
        handle.write("planned_command=" + shlex.join([str(part) for part in command]) + "\n")
