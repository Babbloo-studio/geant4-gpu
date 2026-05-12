#!/usr/bin/env python3
"""Verify EM/gamma Python verifier scripts stay read-only/non-submitting."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "scripts"
REPORT = ROOT / "docs/reports/em_gamma_verifier_script_boundary_20260512.md"
CMAKE = ROOT / "CMakeLists.txt"
STATIC = ROOT / "scripts/verify_em_gamma_static_contract.py"
SELF = Path(__file__)
FORBIDDEN_CALL_NAMES = {
    "os.system",
    "os.remove",
    "os.unlink",
    "shutil.rmtree",
    "shutil.move",
    "shutil.copy",
    "shutil.copy2",
    "shutil.copytree",
}
FORBIDDEN_ARG_TOKENS = {
    "sbatch",
    "srun",
    "write_parquet.py",
    "Particle_output",
    "results.parquet",
}
FORBIDDEN_METHODS = {"write_text", "write_bytes", "unlink", "rename", "replace"}


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


def dotted_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = dotted_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return None


def literal_strings(node: ast.AST) -> list[str]:
    values: list[str] = []
    for child in ast.walk(node):
        if isinstance(child, ast.Constant) and isinstance(child.value, str):
            values.append(child.value)
    return values


def verify_script(path: Path) -> None:
    tree = ast.parse(text(path), filename=str(path))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = dotted_name(node.func) or ""
        if name in FORBIDDEN_CALL_NAMES:
            raise SystemExit(f"forbidden call {name} in {path.relative_to(ROOT)}")
        if name.endswith(".open"):
            for value in literal_strings(node):
                if any(flag in value for flag in ("w", "a", "+", "x")):
                    raise SystemExit(f"write-mode open in {path.relative_to(ROOT)}")
        if any(name.endswith(f".{method}") for method in FORBIDDEN_METHODS):
            raise SystemExit(f"forbidden mutating method {name} in {path.relative_to(ROOT)}")
        if name in {"subprocess.run", "subprocess.check_call", "subprocess.Popen"}:
            joined = " ".join(literal_strings(node))
            for token in FORBIDDEN_ARG_TOKENS:
                if token in joined:
                    raise SystemExit(
                        f"forbidden subprocess token {token!r} in {path.relative_to(ROOT)}"
                    )


def main() -> int:
    for script in sorted(SCRIPT_DIR.glob("verify_em_gamma_*.py")):
        verify_script(script)
        if script != SELF:
            for forbidden in ("NN" "BAR" + "_Detector", "nnbar" + "_reconstruction"):
                require_absent(script, forbidden)

    for marker in (
        "Verifier-script contract",
        "must not submit jobs",
        "normal CTest covers its text and archived GPU report",
        "does not\nauthorize SLURM",
    ):
        require(REPORT, marker)

    for marker in (
        "NAME g4gpu_em_verifier_script_boundary",
        "scripts/verify_em_gamma_verifier_script_boundary.py",
    ):
        require(CMAKE, marker)
        require(STATIC, marker)

    for path in (REPORT, SELF, CMAKE, STATIC):
        for forbidden in ("NN" "BAR" + "_Detector", "nnbar" + "_reconstruction"):
            require_absent(path, forbidden)

    print("EM_GAMMA_VERIFIER_SCRIPT_BOUNDARY_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
