#!/usr/bin/env python3
"""Verify deferred EM/gamma process stubs remain fail-closed."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
KERNEL = ROOT / "src/physics/EMStepKernel.cu"
CMAKE = ROOT / "CMakeLists.txt"


def text(path: Path) -> str:
    if not path.exists():
        raise SystemExit(f"missing required file: {path.relative_to(ROOT)}")
    return path.read_text()


def require(blob: str, needle: str, label: str) -> None:
    if needle not in blob:
        raise SystemExit(f"missing marker in {label}: {needle}")


def require_absent(blob: str, needle: str, label: str) -> None:
    if needle in blob:
        raise SystemExit(f"unexpected marker in {label}: {needle}")


def function_body(source: str, name: str) -> str:
    start = source.find(f"void {name}(")
    if start < 0:
        raise SystemExit(f"missing function: {name}")
    brace = source.find("{", start)
    if brace < 0:
        raise SystemExit(f"missing function body: {name}")
    depth = 0
    for pos in range(brace, len(source)):
        char = source[pos]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[brace + 1 : pos]
    raise SystemExit(f"unterminated function body: {name}")


def verify_stub(source: str, name: str, todo: str) -> None:
    body = function_body(source, name)
    label = f"{name} body"
    for marker in ("out = {};", todo, "return;"):
        require(body, marker, label)
    for forbidden in (
        "out.process =",
        "out.primary_energy_mev =",
        "out.secondary_energy_mev =",
        "out.status = 0",
        "tracks.",
        "Launch",
        "<<<",
        "secondary_buffer",
        "push_secondary",
    ):
        require_absent(body, forbidden, label)


def main() -> int:
    source = text(KERNEL)
    cmake = text(CMAKE)

    verify_stub(source, "SamplePhotoelectric", "TODO Phase 2.EM-photoelectric")
    verify_stub(source, "SamplePair", "TODO Phase 2.EM-pair")
    verify_stub(source, "SampleBremsstrahlung", "TODO Phase 2.EM-bremsstrahlung")

    step = function_body(source, "EMStep")
    require(step, "SampleCompton(tracks.ekin[i], material", "EMStep body")
    require(step, "SampleBremsstrahlung(tracks.ekin[i], pdg, material", "EMStep body")
    require_absent(step, "SamplePhotoelectric(", "EMStep body")
    require_absent(step, "SamplePair(", "EMStep body")

    for marker in (
        "NAME g4gpu_em_stub_fail_closed",
        "scripts/verify_em_gamma_stub_fail_closed.py",
    ):
        require(cmake, marker, "CMakeLists.txt")

    for forbidden in ("NN" "BAR" + "_Detector", "nnbar" + "_reconstruction"):
        require_absent(source, forbidden, "EMStepKernel.cu")
        require_absent(cmake, forbidden, "CMakeLists.txt")

    print("EM_GAMMA_STUB_FAIL_CLOSED_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
