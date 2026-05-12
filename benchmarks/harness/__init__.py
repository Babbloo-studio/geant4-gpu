"""Phase-5+ benchmark harness package."""

from .schema import BenchmarkResultRow, RESULT_SCHEMA
from .parity import ParityResult, parity_gate
from .builder import BuildError, build_optimized, build_vanilla
from .hardware import HardwareFingerprint, collect_local_fingerprint
from .optimization_registry import OptimizationRegistryEntry, require_entry
from .sampler_observables import SamplerObservableGateResult, bd001_sampler_observable_gate
from .bd001_branch_gate import BD001BranchGateResult, bd001_branch_gate

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
    "OptimizationRegistryEntry",
    "require_entry",
    "SamplerObservableGateResult",
    "bd001_sampler_observable_gate",
    "BD001BranchGateResult",
    "bd001_branch_gate",
]
