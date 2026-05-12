#!/usr/bin/env python3
"""Static contract verifier for the EM/gamma scaffold."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HEADER = ROOT / "include/g4gpu/EMStepKernel.hh"
KERNEL = ROOT / "src/physics/EMStepKernel.cu"
TEST = ROOT / "tests/test_em_klein_nishina.cu"
CMAKE = ROOT / "CMakeLists.txt"


def text(path: Path) -> str:
    if not path.exists():
        raise SystemExit(f"missing required file: {path.relative_to(ROOT)}")
    return path.read_text()


def require(path: Path, needle: str) -> None:
    if needle not in text(path):
        raise SystemExit(f"missing marker in {path.relative_to(ROOT)}: {needle}")


def require_absent(path: Path, needle: str) -> None:
    if needle in text(path):
        raise SystemExit(
            f"unexpected marker in {path.relative_to(ROOT)}: {needle}"
        )


def main() -> int:
    for symbol in (
        "SamplePhotoelectric",
        "SampleCompton",
        "SamplePair",
        "SampleBremsstrahlung",
        "EMStep(",
        "LaunchEMStepKernel",
        "LaunchComptonSampleKernel",
    ):
        require(HEADER, symbol)

    for marker in (
        "SampleKleinNishinaEnergyFraction",
        "Kahn/Butcher-Messel rejection sampler",
        "SampleCompton(tracks.ekin[i], material",
        "TODO Phase 2.EM-photoelectric",
        "TODO Phase 2.EM-pair",
        "TODO Phase 2.EM-bremsstrahlung",
    ):
        require(KERNEL, marker)

    for marker in (
        "constexpr int kSamples = 10000;",
        "constexpr double kRequiredPValue = 0.05;",
        "constexpr int kCudaUnavailableSkipCode = 77;",
        "SKIP: CUDA device unavailable",
        "PASS: Klein-Nishina scattered-energy KS",
        "return kCudaUnavailableSkipCode;",
        "LaunchEMStepKernel(&buffer.device(), d_rng, nullptr, kSamples, nullptr)",
    ):
        require(TEST, marker)

    for marker in (
        "find_package(Python3 COMPONENTS Interpreter QUIET)",
        "if(G4GPU_WITH_EM)",
        "target_sources(G4GPU PRIVATE src/physics/EMStepKernel.cu)",
        "target_link_libraries(G4GPU PRIVATE CUDA::curand)",
        "add_test(NAME g4gpu_em_klein_nishina",
        "set_tests_properties(g4gpu_em_klein_nishina PROPERTIES SKIP_RETURN_CODE 77)",
        "add_test(",
        "NAME g4gpu_em_deferred_process_gap",
        "scripts/verify_em_gamma_deferred_process_gap.py",
        "NAME g4gpu_em_static_contract",
        "scripts/verify_em_gamma_static_contract.py",
        "NAME g4gpu_em_stub_fail_closed",
        "scripts/verify_em_gamma_stub_fail_closed.py",
        "NAME g4gpu_em_publication_audit",
        "scripts/verify_em_gamma_publication_audit.py",
        "NAME g4gpu_em_publication_artifacts",
        "scripts/verify_em_gamma_publication_artifacts.py",
        "NAME g4gpu_em_publication_transcript",
        "scripts/verify_em_gamma_publication_transcript.py",
        "NAME g4gpu_em_publication_patch_id",
        "scripts/verify_em_gamma_publication_patch_id.py",
        "NAME g4gpu_em_source_boundary",
        "scripts/verify_em_gamma_source_boundary.py",
        "NAME g4gpu_em_ctest_execution_boundary",
        "scripts/verify_em_gamma_ctest_execution_boundary.py",
        "NAME g4gpu_em_report_coverage",
        "scripts/verify_em_gamma_report_coverage.py",
        "NAME g4gpu_em_lane_objective_audit",
        "scripts/verify_em_gamma_lane_objective_audit.py",
        "NAME g4gpu_em_claim_boundary",
        "scripts/verify_em_gamma_claim_boundary.py",
        "NAME g4gpu_em_verifier_script_boundary",
        "scripts/verify_em_gamma_verifier_script_boundary.py",
        "NAME g4gpu_em_runtime_sbatch_contract",
        "scripts/verify_em_gamma_runtime_sbatch.py",
        "NAME g4gpu_em_runtime_gpu_report",
        "scripts/verify_em_gamma_runtime_gpu_report.py",
        "NAME g4gpu_em_photoelectric_contract",
        "scripts/verify_em_gamma_photoelectric_contract.py",
        "NAME g4gpu_em_pair_contract",
        "scripts/verify_em_gamma_pair_contract.py",
        "NAME g4gpu_em_bremsstrahlung_contract",
        "scripts/verify_em_gamma_bremsstrahlung_contract.py",
        "NAME g4gpu_em_deferred_contract_index",
        "scripts/verify_em_gamma_deferred_contract_index.py",
        "NAME g4gpu_em_implementation_roadmap",
        "scripts/verify_em_gamma_implementation_roadmap.py",
        "NAME g4gpu_em_validation_fixture_contract",
        "scripts/verify_em_gamma_validation_fixture_contract.py",
        "NAME g4gpu_em_table_owner_preflight",
        "scripts/verify_em_gamma_table_owner_preflight.py",
        "NAME g4gpu_em_secondary_buffer_preflight",
        "scripts/verify_em_gamma_secondary_buffer_preflight.py",
        "NAME g4gpu_em_rng_stream_preflight",
        "scripts/verify_em_gamma_rng_stream_preflight.py",
        "NAME g4gpu_em_process_selector_preflight",
        "scripts/verify_em_gamma_process_selector_preflight.py",
        "NAME g4gpu_em_status_code_preflight",
        "scripts/verify_em_gamma_status_code_preflight.py",
        "NAME g4gpu_em_preflight_contract_index",
        "scripts/verify_em_gamma_preflight_contract_index.py",
        "NAME g4gpu_em_preflight_chain_audit",
        "scripts/verify_em_gamma_preflight_chain_audit.py",
        "NAME g4gpu_em_option_boundary",
        "scripts/verify_em_gamma_option_boundary.py",
        "NAME g4gpu_em_option_off_config",
        "scripts/verify_em_gamma_option_off_config.py",
        "NAME g4gpu_em_line_caps",
        "scripts/verify_em_gamma_line_caps.py",
    ):
        require(CMAKE, marker)

    for path in (HEADER, KERNEL, TEST, CMAKE, Path(__file__)):
        for forbidden in ("NN" "BAR" + "_Detector", "nnbar" + "_reconstruction"):
            require_absent(path, forbidden)

    print("EM_GAMMA_STATIC_CONTRACT_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
