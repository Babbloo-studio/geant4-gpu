"""Phase-5+ benchmark harness package."""

from .schema import BenchmarkResultRow, RESULT_SCHEMA
from .parity import ParityResult, parity_gate
from .builder import BuildError, build_optimized, build_vanilla
from .hardware import HardwareFingerprint, collect_local_fingerprint

__all__ = [
    "BenchmarkResultRow",
    "RESULT_SCHEMA",
    "ParityResult",
    "parity_gate",
    "BuildError",
    "build_optimized",
    "build_vanilla",
    "HardwareFingerprint",
    "collect_local_fingerprint",
]
