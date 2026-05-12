# EM/gamma source-boundary audit — 2026-05-12

## Scope

This audit locks the current EM/gamma source boundary. It is a static verifier
artifact only: no kernel runtime path, physics table, secondary buffer,
process selector, detector/event workload, benchmark result row, SLURM job, or
production output is changed here.

The source-boundary verifier scans the EM/gamma implementation roots
`include/`, `src/`, and `tests/` for forbidden integration markers. It is meant
to keep the compact Compton scaffold isolated until the deferred EM contracts
are implemented deliberately and reviewed as separate compact units.

## Guarded absent implementations

The current source tree must not contain any of these implementation surfaces:

- `G4GPUEMPhysicsTables` or `EMPhysicsTableView`.
- `G4GPUEMSecondaryBuffer` or `secondary_buffer` mutation paths.
- `G4GPUEMRngStream` or `rng_stream` ownership paths.
- `G4GPUEMProcessSelector`, `SelectEMProcess`, or `process_selector` paths.
- `G4GPUEMStatusCode` status-vocabulary implementation.

Those names may appear only in documentation, contract reports, or verifier
scripts that describe the fail-closed blockers. They must not enter the source
roots before the matching preflight contract and validation fixture are ready.

## Isolation boundary

The verifier also keeps the EM/gamma source roots free of NNBAR production-code
references. The CMake EM test surface may validate wrapper text and static
contracts, but it must not call detector/event workloads, benchmark writers,
`sbatch`, `srun`, or production-output paths.

## Boundary

Passing `g4gpu_em_source_boundary` only proves that the current source roots
remain isolated and preflight-only. It does not authorize SLURM submission,
detector or event-driver execution, output-row generation, reference
regeneration, physics-parity claims, speedup claims, ABI migration, or any
executable photoelectric, pair-production, or bremsstrahlung implementation.
