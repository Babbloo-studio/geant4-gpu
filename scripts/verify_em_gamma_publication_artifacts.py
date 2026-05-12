#!/usr/bin/env python3
"""Verify current EM/gamma fallback publication artifacts."""

from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
CMAKE = ROOT / "CMakeLists.txt"
STATIC = ROOT / "scripts/verify_em_gamma_static_contract.py"
SELF = Path(__file__)
PUB = Path("/projects/hep/fs10/shared/nnbar/billy/g4gpu-em-gamma-publication")


def text(path: Path) -> str:
    if not path.exists():
        raise SystemExit(f"missing required file: {path}")
    return path.read_text(encoding="utf-8")


def require(path: Path, needle: str) -> None:
    if needle not in text(path):
        raise SystemExit(f"missing marker in {path}: {needle}")


def require_absent(path: Path, needle: str) -> None:
    if needle in text(path):
        raise SystemExit(f"unexpected marker in {path}: {needle}")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
    return proc.stdout.strip()


def bundle_heads(bundle: Path) -> str:
    proc = subprocess.run(
        ["git", "bundle", "list-heads", str(bundle)],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise SystemExit(proc.stdout.strip())
    return proc.stdout.strip()


def find_one(pattern: str, description: str) -> Path:
    matches = sorted(PUB.glob(pattern))
    if len(matches) != 1:
        raise SystemExit(
            f"expected one {description} for pattern {pattern}, found {len(matches)}"
        )
    return matches[0]


def main() -> int:
    head = git("rev-parse", "--short", "HEAD")
    full_head = git("rev-parse", "HEAD")
    ok_marker = f"EM_GAMMA_CURRENT_{head.upper()}_OK"
    subject = git("show", "-s", "--format=%s", "HEAD")
    bundle = PUB / f"lane-g4gpu-em-gamma-{head}.bundle"
    patch = find_one(f"patches/*-{head}.patch", "current-head patch")
    artifacts = [
        bundle,
        patch,
        PUB / f"BUNDLE_VERIFY_{head}.txt",
        PUB / f"MIRROR_VERIFY_{head}.txt",
        PUB / f"check_em_gamma_current_{head}.sh",
        PUB / f"check_em_gamma_current_{head}.latest.txt",
    ]
    manifest = find_one(f"SHA256SUMS-{head}-*", "current-head checksum manifest")

    for path in artifacts:
        if not path.is_file():
            raise SystemExit(f"missing publication artifact: {path}")
    require(PUB / f"BUNDLE_VERIFY_{head}.txt", "The bundle records a complete history.")
    if full_head not in bundle_heads(bundle):
        raise SystemExit(f"current HEAD {full_head} not listed by {bundle}")
    require(patch, full_head)
    require(patch, f"Subject: [PATCH] {subject}")
    mirror_verify = PUB / f"MIRROR_VERIFY_{head}.txt"
    require(mirror_verify, "fork refs/heads/lane/g4gpu-em-gamma")
    require(mirror_verify, f"{full_head}\trefs/heads/lane/g4gpu-em-gamma")
    require(mirror_verify, "local HEAD")
    require(mirror_verify, full_head)
    require(PUB / f"check_em_gamma_current_{head}.latest.txt", ok_marker)
    require(PUB / f"check_em_gamma_current_{head}.latest.txt", "100% tests passed")
    require(PUB / f"check_em_gamma_current_{head}.sh", "ctest --test-dir build")

    manifest_entries: dict[str, str] = {}
    for line in text(manifest).splitlines():
        if not line.strip():
            continue
        digest, rel = line.split(maxsplit=1)
        manifest_entries[rel.strip()] = digest
    for path in artifacts:
        rel = str(path.relative_to(PUB))
        if rel not in manifest_entries:
            raise SystemExit(f"checksum manifest missing {rel}")
        if sha256(path) != manifest_entries[rel]:
            raise SystemExit(f"checksum mismatch for {rel}")

    for marker in (
        "NAME g4gpu_em_publication_artifacts",
        "scripts/verify_em_gamma_publication_artifacts.py",
    ):
        require(CMAKE, marker)
        require(STATIC, marker)

    for path in (CMAKE, STATIC, SELF):
        for forbidden in ("NN" "BAR" + "_Detector", "nnbar" + "_reconstruction"):
            require_absent(path, forbidden)

    print("EM_GAMMA_PUBLICATION_ARTIFACTS_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
