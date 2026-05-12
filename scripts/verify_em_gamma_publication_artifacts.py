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
HEAD = "83087ed"
ARTIFACTS = (
    f"lane-g4gpu-em-gamma-{HEAD}.bundle",
    f"patches/0020-em-gamma-current-publication-audit-{HEAD}.patch",
    f"BUNDLE_VERIFY_{HEAD}.txt",
    f"check_em_gamma_current_{HEAD}.sh",
    f"check_em_gamma_current_{HEAD}.latest.txt",
)
MANIFEST = PUB / f"SHA256SUMS-{HEAD}-current-publication-audit"


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


def main() -> int:
    if git("rev-parse", "--short", "HEAD") != HEAD:
        raise SystemExit("repository head does not match publication head")
    if git("rev-parse", "--short", "fork/lane/g4gpu-em-gamma") != HEAD:
        raise SystemExit("fork ref does not match publication head")

    for rel in ARTIFACTS:
        path = PUB / rel
        if not path.is_file():
            raise SystemExit(f"missing publication artifact: {path}")
    if not MANIFEST.is_file():
        raise SystemExit(f"missing checksum manifest: {MANIFEST}")

    require(PUB / f"BUNDLE_VERIFY_{HEAD}.txt", "The bundle records a complete history.")
    require(PUB / f"check_em_gamma_current_{HEAD}.latest.txt", "EM_GAMMA_CURRENT_83087ED_OK")
    require(PUB / f"check_em_gamma_current_{HEAD}.latest.txt", "100% tests passed")
    require(PUB / f"check_em_gamma_current_{HEAD}.sh", "ctest --test-dir build")

    manifest_entries: dict[str, str] = {}
    for line in text(MANIFEST).splitlines():
        if not line.strip():
            continue
        digest, rel = line.split(maxsplit=1)
        manifest_entries[rel.strip()] = digest
    for rel in ARTIFACTS:
        if rel not in manifest_entries:
            raise SystemExit(f"checksum manifest missing {rel}")
        if sha256(PUB / rel) != manifest_entries[rel]:
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
