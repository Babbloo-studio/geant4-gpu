# BD-geant4-001 source-prefix and physics-list selector preflight

Date: 2026-05-12
Lane: `g4gpu-phase5-bd001-source-prefix` (PANE 3 lane-swap)
Scope: compact fail-closed harness prerequisite only. No SLURM submission,
event execution, reference regeneration, result-row write, parity/speedup
promotion, optimized Moller/Bhabha sampler implementation, or NNBAR production
edit was performed.

## Prompt-to-artifact mapping

| Requirement | Evidence / disposition |
|---|---|
| Do one compact fail-closed optimized Geant4 source-prefix selection or physics-list selector proof | Implemented both as script-generation contracts only. |
| Prevent BD-001 from using the vanilla Geant4 install as the optimized path | `RunnerSpec.optimized_geant4_prefix`, `--optimized-geant4-prefix`, and registry field `optimized_geant4_prefix` are validated; BD-001 non-reference scripts fail closed if it is missing or identical to `--geant4-prefix`. |
| Prove PL1/PL2 cannot be silently recorded without driver selection | `benchmarks/harness/runner.py` passes `--physics-list "${PHYSICS_LIST}"` to vanilla, optimized, and reference benchmark driver invocations before collect records the same ID. |
| Keep harness fail-closed | Generated scripts check `Geant4Config.cmake` under vanilla and optimized prefixes and switch the Geant4 environment per variant. Drivers that cannot honor the physics-list option fail before `benchmarks.harness.run --collect` can append a result row. |
| Avoid production claims | No measurement row, speedup, parity, source implementation, or SLURM job was produced. |

## Changed contract

Before this preflight, generated scripts exported one `GEANT4_PREFIX` and passed
`PHYSICS_LIST` only to the collection metadata path. A BD-001 row could
therefore record a PL1/PL2 label without proving that the executable selected
that physics list, and it had no script-level separation between vanilla and an
optimized Geant4-source install.

Generated optimized-result scripts now include distinct prefixes:

```bash
VANILLA_GEANT4_PREFIX=/path/to/vanilla
OPTIMIZED_GEANT4_PREFIX=/path/to/optimized
run_one vanilla "${VANILLA_BIN}" "${seed}" "${VANILLA_GEANT4_PREFIX}"
run_one optimized "${OPTIMIZED_BIN}" "${seed}" "${OPTIMIZED_GEANT4_PREFIX}"
```

and invoke benchmark drivers as:

```bash
"${binary}" --events "${N_EVENTS}" --commit "${OPT_ID}_${variant}_seed_${seed}" \
  --physics-list "${PHYSICS_LIST}" --output "${out}"
```

This is intentionally fail-closed: until a reviewed optimized prefix and driver
selector exist, BD-001 cannot silently produce PL-tagged raw Parquets or a
source-level Geant4 result row.

## Verification

- `python -m py_compile benchmarks/harness/optimization_registry.py benchmarks/harness/run.py benchmarks/harness/runner.py benchmarks/harness/tests/test_run.py benchmarks/harness/tests/test_runner.py`
- `python benchmarks/harness/tests/test_runner.py` -> `benchmark_harness_runner: PASS`
- `python -m pytest benchmarks/harness/tests -q` -> `49 passed`
- `ctest --test-dir build -R 'g4gpu_benchmark_harness_(run|runner|optimization_registry)' --output-on-failure` -> `3/3` passed
- Generated W1/PL1/H3 BD-001 dry-run script passed `bash -n` and grep confirmed
  distinct vanilla/optimized prefixes, per-variant `setup_geant4_env`, and the
  benchmark-driver command line carries `--physics-list "${PHYSICS_LIST}"`.

## Remaining BD-001 blockers

BD-geant4-001 remains blocked on an actual optimized sampler branch/install
prefix, a real reviewed registry row, driver-side physics-list implementation
evidence, guarded dry-run/smoke, and only then any measurement row.
