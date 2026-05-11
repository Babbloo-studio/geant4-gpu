# Phase 5 artifact checksum manifest

Date: 2026-05-11 17:22 CEST

This manifest records checksums for ignored LUNARC evidence artifacts used by `docs/reports/phase5_measurement_audit.md`. It intentionally stores hashes and paths only, not bulky Parquet/log data.

- Profiled benchmark commit: `57800c2`
- Baseline SLURM job: `3041865`
- CPU profiling SLURM job: `3041873`
- Validation mode: `benchmarks/validate.py` self-comparison sanity checks

## Parquet benchmark outputs

| Path | Bytes | SHA256 |
| --- | ---: | --- |
| `benchmarks/results/beam_neutron_57800c2.parquet` | 73177 | `525bce0eb9abf32df016117340645f4174a8565d431117834a69f8a5c67b2c2d` |
| `benchmarks/results/cosmic_shower_57800c2.parquet` | 63093 | `fe48e0d1cfab5336768322dbcb25aec73f8c3ffc5c102a4dc594d38545e316c5` |
| `benchmarks/results/gamma_100mev_57800c2.parquet` | 73042 | `a4aa0b71c9e6c2a707672adff8963af25eef4f8c0f8a98bc46b1c7da083b4ed3` |
| `benchmarks/results/muon_10gev_57800c2.parquet` | 61751 | `f226161db015cf7fc27a9ca483986055dfdf68711d5c5131528c4b5818cf8b3e` |
| `benchmarks/results/nbar_carbon_57800c2.parquet` | 70045 | `b4149626418fe69d066560cf1b59246f80ffdf15b9e249c1e6f74d2b540fcbe1` |
| `benchmarks/results/optical_scintillator_57800c2.parquet` | 81683 | `ecda9a37e2dd3bac96f3f9326cfcf99a40786bcb391430adce460e2897e21d49` |

## Canonical Geant4 logs

| Path | Bytes | SHA256 |
| --- | ---: | --- |
| `benchmarks/results/canonical/basic_b1_57800c2.log` | 178972 | `581bb5b8e38f3103a9d128f41a8e17f54f5fa5661da52e30ec68d06aa917bb54` |
| `benchmarks/results/canonical/hadr01_57800c2.log` | 34291 | `19da460386f7af5ac026854077dcf345081afc06a6a1b25abb648ada18ff4153` |
| `benchmarks/results/canonical/hadr02_57800c2.log` | 44734 | `2b9a5429b696f5b37bd79ef521f75daf0495d340933af4b560d1e14552229c15` |
| `benchmarks/results/canonical/opnovice2_57800c2.log` | 63672 | `2e5cacf7a7c668edaebd7d1705501d9187688c91d28776a4c4dd5c447c1cf4e7` |
| `benchmarks/results/canonical/par01_57800c2.log` | 375728 | `eace7f00dcc084070c362e7586b9f486657a866640456978e43f1c1487337ecc` |
| `benchmarks/results/canonical/testem0_57800c2.log` | 11855 | `1f0a03134599d9c216dcce4bd5023b251458599f026fa469980fefd9b8e326e6` |

## Validation self-comparison JSON

| Path | Bytes | SHA256 |
| --- | ---: | --- |
| `benchmarks/results/beam_neutron_validate_self_57800c2.json` | 1069 | `74ff0db6419c019d13242e083203a27e92f8bdf9d1ec3d14d001ae4f0ebc17ff` |
| `benchmarks/results/cosmic_shower_validate_self_57800c2.json` | 1071 | `e617573b0e51caedcf3eb71716ccfce18a0f01941538534b0824732f1c046f3e` |
| `benchmarks/results/gamma_100mev_validate_self_57800c2.json` | 1069 | `60d195c8f13ee00fced32b4bfb13a12baa69ed8ea51fe7e990910ea310c07a59` |
| `benchmarks/results/muon_10gev_validate_self_57800c2.json` | 1065 | `c94123faed8e1606e48f600254d1d13b04c8fa81f08e3c76d6a92b3a62954517` |
| `benchmarks/results/nbar_carbon_validate_self_57800c2.json` | 1067 | `73672e601474e3b39ee7486490becf3d25b1e48936e135f8d1979ad0a6082051` |
| `benchmarks/results/optical_scintillator_validate_self_57800c2.json` | 1085 | `ac3370eda3e0a4f3b866e6db079cc583d76cec76fa88bf19f1b964d0846bc85c` |

## Committed CPU perf profiles

| Path | Bytes | SHA256 |
| --- | ---: | --- |
| `benchmarks/profiles/beam_neutron_cpu_57800c2.txt` | 584562 | `3b2754a182ac37276e5eb81b1d6551053082a4e662ed1c262a879b467990c132` |
| `benchmarks/profiles/cosmic_shower_cpu_57800c2.txt` | 591765 | `aac3c3979e939f205abb1e732dbb161f9050713f1747f5d38c8465345258daae` |
| `benchmarks/profiles/gamma_100mev_cpu_57800c2.txt` | 590066 | `7f3ee83d80f21a14c6936213edb0abeea33681f2b99480a84cfd1699ac962098` |
| `benchmarks/profiles/muon_10gev_cpu_57800c2.txt` | 580347 | `9b3ae94e3325a3f1a32b67030bd5db81066beb3b1dfa6327e90258e75ecc82cf` |
| `benchmarks/profiles/nbar_carbon_cpu_57800c2.txt` | 605802 | `6979b8b0b4c8f3ba91cd6075642e7cd46abe317f21343148faf5f31fe8cccf01` |
| `benchmarks/profiles/optical_scintillator_cpu_57800c2.txt` | 585504 | `cee9c2418458bd9741b5b4dc62bfcc921d84b2867767a0e7d4d506d85013c333` |

## SLURM scripts and stdout evidence

| Path | Bytes | SHA256 |
| --- | ---: | --- |
| `benchmarks/results/phase5a_57800c2.slurm` | 4398 | `71e194b3bc1cf53ca2841e63c55e48234df497a4e0671bbf8f47a2eb0f3a9eb4` |
| `benchmarks/results/phase5a_57800c2_3041865.out` | 2069 | `f22678a11206965695f85f75a7dadd1c6d03f2c26043dd1837b9a14aa6666164` |

## CPU profiling SLURM evidence

| Path | Bytes | SHA256 |
| --- | ---: | --- |
| `benchmarks/profiles/phase5b_cpu_57800c2.slurm` | 2748 | `bcba3c413027db9c8e23bfc9e3eb9d20209f9cb0dd07f6eb2adcdaea182e74af` |
| `benchmarks/profiles/phase5b_cpu_57800c2_3041873.out` | 1782 | `ecd6d6e5e71172df1cd68df5e0257bf2c9f584af0bf1f4927d5b0edcdcd8cec7` |


## Pending full GPU CTest job evidence

| Path / field | Value |
| --- | --- |
| SLURM job id | `3041846` |
| Current state at 2026-05-11 17:24 CEST | `PENDING (Priority)` |
| Estimated start | `2026-05-12T09:59:00` on `cg04` |
| Submitted script | `build/g4gpu_phase5_ctest_current.slurm` |
| Submitted script bytes | 890 |
| Submitted script SHA256 | `0e496a4aac218eab86f213535235a554f2916205ecf3809547bca93e9cb7cc14` |
| Runtime note | The original script contains `#SBATCH --time=00:15:00`, but the live job was shortened with `scontrol update JobId=3041846 TimeLimit=00:05:00`; `scontrol show job 3041846` reports `TimeLimit=00:05:00`. |

## Audit status

All expected artifact sections had at least one file at generation time.

Known open external blockers remain unchanged: full GPU CTest job `3041846` is pending scheduler priority, GitHub push is blocked by missing credentials, and Phase 5d must wait for planner review.
