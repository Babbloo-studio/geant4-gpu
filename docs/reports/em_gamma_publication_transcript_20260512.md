# EM/gamma publication transcript contract (2026-05-12)

## Scope

This report defines the minimum evidence that the current-head fallback
publication checker must leave behind in its archived transcript.  It is a
publication-hardening gate only; it does not authorize batch submission,
benchmark production, detector-event execution, or a physics-parity claim.

## Required current-head evidence

The repo-native verifier `scripts/verify_em_gamma_publication_transcript.py`
checks the live short `HEAD` and the matching artifacts under the fallback
publication directory:

| Evidence class | Required marker | Reason |
|---|---|---|
| Head lock | `test "$(git rev-parse --short HEAD)" = "<head>"` | prevents stale checker reuse |
| Static verifier sweep | `python3 -m py_compile` and direct EM verifier calls | catches syntax and contract drift |
| Line-cap audit | `wc -l` in the checker and `total` in the transcript | preserves the 500-line compact-unit rule |
| Isolation grep | `rg -n` plus the deny patterns | keeps the lane separated from production paths |
| Build shape | `cmake -B build -DG4GPU_WITH_EM=ON` and `cmake --build build --target G4GPU test_em_klein_nishina -j2` | proves the scaffold still builds in EM mode |
| CTest sweep | `ctest --test-dir build --output-on-failure -R '^g4gpu_em_'` | records the focused EM gate set |
| Patch identity | `python3 scripts/verify_em_gamma_publication_patch_id.py` and `EM_GAMMA_PUBLICATION_PATCH_ID_OK` | proves the fallback patch encodes the current commit delta |
| Holder/no-GPU boundary | `g4gpu_em_klein_nishina (Skipped)` | prevents treating a holder-node skip as GPU physics evidence |
| Clean tree check | `git diff --check` | catches whitespace/patch-format drift |
| Success stamp | `EM_GAMMA_CURRENT_<HEAD>_OK` | ties the transcript to the current commit |

## Boundary

The transcript contract is intentionally about checker shape and archived output.
It does not create a new runtime allocation path, does not relax the existing
fail-closed runtime gate, and does not claim speedup, parity, or readiness for
production use.
