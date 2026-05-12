#!/usr/bin/env python3
"""Configure an EM-OFF build and verify no EM/gamma targets leak through."""

from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
CMAKE = ROOT / "CMakeLists.txt"
STATIC = ROOT / "scripts/verify_em_gamma_static_contract.py"
CTEST_BOUNDARY = ROOT / "scripts/verify_em_gamma_ctest_execution_boundary.py"
REPORT_COVERAGE = ROOT / "scripts/verify_em_gamma_report_coverage.py"
REPORT = ROOT / "docs/reports/em_gamma_option_off_config_20260512.md"
REFERENCE_CACHE = ROOT / "build/CMakeCache.txt"
SELF = Path(__file__)


def text(path: Path) -> str:
    if not path.exists():
        raise SystemExit(f"missing required file: {path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8", errors="replace")


def require(path: Path, needle: str) -> None:
    if needle not in text(path):
        raise SystemExit(f"missing marker in {path.relative_to(ROOT)}: {needle}")


def require_absent(path: Path, needle: str) -> None:
    if needle in text(path):
        raise SystemExit(f"unexpected marker in {path.relative_to(ROOT)}: {needle}")


def cache_value(name: str) -> str | None:
    if not REFERENCE_CACHE.exists():
        return None
    prefix = f"{name}:"
    for line in text(REFERENCE_CACHE).splitlines():
        if line.startswith(prefix):
            return line.split("=", 1)[1]
    return None


def run(args: list[str]) -> str:
    proc = subprocess.run(
        args,
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise SystemExit(proc.stdout.strip())
    return proc.stdout


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="g4gpu-em-off-") as tmpdir:
        build = Path(tmpdir) / "build"
        cmake_args = [
            "cmake",
            "-S",
            str(ROOT),
            "-B",
            str(build),
            "-DG4GPU_WITH_EM=OFF",
            "-DG4GPU_WITH_OPTICAL=OFF",
            "-DG4GPU_WITH_RTX=OFF",
        ]
        for key in ("CMAKE_CUDA_COMPILER", "CUDAToolkit_ROOT", "Geant4_DIR"):
            if value := cache_value(key):
                cmake_args.append(f"-D{key}={value}")
        configure = run(cmake_args)
        if "G4GPU_WITH_EM" not in text(build / "CMakeCache.txt"):
            raise SystemExit("OFF build cache does not record G4GPU_WITH_EM")
        require(build / "CMakeCache.txt", "G4GPU_WITH_EM:BOOL=OFF")

        run(["cmake", "--build", str(build), "--target", "G4GPU", "-j2"])
        targets = run(["cmake", "--build", str(build), "--target", "help"])
        ctest_list = run(["ctest", "--test-dir", str(build), "-N"])
    combined = configure + targets + ctest_list
    for forbidden in (
        "g4gpu_em_",
        "test_em_klein_nishina",
        "EMStepKernel.cu",
    ):
        if forbidden in combined:
            raise SystemExit(f"EM marker leaked into OFF configure/build listing: {forbidden}")

    for marker in (
        "NAME g4gpu_em_option_off_config",
        "scripts/verify_em_gamma_option_off_config.py",
    ):
        require(CMAKE, marker)
        require(STATIC, marker)
    require(CTEST_BOUNDARY, "g4gpu_em_option_off_config")
    require(REPORT_COVERAGE, "em_gamma_option_off_config_20260512.md")

    for marker in (
        "G4GPU_WITH_EM=OFF",
        "temporary build tree",
        "does not authorize SLURM submission",
        "does not make speedup, parity, or\nproduction-readiness claims",
    ):
        require(REPORT, marker)

    for path in (REPORT, SELF, CMAKE, STATIC, CTEST_BOUNDARY, REPORT_COVERAGE):
        for forbidden in ("NN" "BAR" + "_Detector", "nnbar" + "_reconstruction"):
            require_absent(path, forbidden)

    print("EM_GAMMA_OPTION_OFF_CONFIG_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
