#!/usr/bin/env python3
"""Verify the current fallback patch has the same stable patch-id as HEAD."""

from __future__ import annotations

from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
CMAKE = ROOT / "CMakeLists.txt"
STATIC = ROOT / "scripts/verify_em_gamma_static_contract.py"
REPORT = ROOT / "docs/reports/em_gamma_publication_patch_id_20260512.md"
SELF = Path(__file__)
PUB = Path("/projects/hep/fs10/shared/nnbar/billy/g4gpu-em-gamma-publication")


def text(path: Path) -> str:
    if not path.exists():
        raise SystemExit(f"missing required file: {path}")
    return path.read_text(encoding="utf-8", errors="replace")


def require(path: Path, needle: str) -> None:
    if needle not in text(path):
        raise SystemExit(f"missing marker in {path}: {needle}")


def require_absent(path: Path, needle: str) -> None:
    if needle in text(path):
        raise SystemExit(f"unexpected marker in {path}: {needle}")


def git(*args: str) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise SystemExit(proc.stdout.strip())
    return proc.stdout


def patch_id(input_text: str) -> str:
    proc = subprocess.run(
        ["git", "patch-id", "--stable"],
        cwd=ROOT,
        input=input_text,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise SystemExit(proc.stdout.strip())
    fields = proc.stdout.split()
    if len(fields) < 2:
        raise SystemExit(f"unexpected patch-id output: {proc.stdout!r}")
    return fields[0]


def find_one(pattern: str) -> Path:
    matches = sorted(PUB.glob(pattern))
    if len(matches) != 1:
        raise SystemExit(f"expected one publication patch for {pattern}, found {len(matches)}")
    return matches[0]


def main() -> int:
    head = git("rev-parse", "--short", "HEAD").strip()
    full_head = git("rev-parse", "HEAD").strip()
    subject = git("show", "-s", "--format=%s", "HEAD").strip()
    patch = find_one(f"patches/*-{head}.patch")
    require(patch, full_head)
    require(patch, f"Subject: [PATCH] {subject}")

    live_patch_id = patch_id(git("show", "--format=email", "--no-ext-diff", "HEAD"))
    artifact_patch_id = patch_id(text(patch))
    if live_patch_id != artifact_patch_id:
        raise SystemExit(
            f"patch-id mismatch for {patch}: live={live_patch_id} artifact={artifact_patch_id}"
        )

    for marker in (
        "same file\ndelta as the live `HEAD` commit",
        "git patch-id --stable",
        "does not apply the\npatch into any worktree",
        "does not authorize SLURM submission",
    ):
        require(REPORT, marker)

    for marker in (
        "NAME g4gpu_em_publication_patch_id",
        "scripts/verify_em_gamma_publication_patch_id.py",
    ):
        require(CMAKE, marker)
        require(STATIC, marker)

    for path in (REPORT, SELF, CMAKE, STATIC):
        for forbidden in ("NN" "BAR" + "_Detector", "nnbar" + "_reconstruction"):
            require_absent(path, forbidden)

    print("EM_GAMMA_PUBLICATION_PATCH_ID_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
