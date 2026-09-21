# POWCARB model and numerical inputs

This release contains numerical model inputs, the MATLAB linear-program constructor and public input/output interface, and non-plotting scientific calculation functions for the policy-grid carbon-market analysis. It does **not** distribute drawing/layout code, figure assets, archived simulation outputs, archived fixed-allocation reference solutions, solved dispatch arrays or transfer results. Scope exclusion is intentional, not a claim that these materials are needed to be downloaded later from this repository.

## Included

- 192 year/CQ/COP thermal-coefficient tables for 2020–2035, with numerical model IDs instead of plant names.
- 144 province-hour tables: each year has wind, solar, hydro and nuclear inputs for RE1/RE2 and common demand. Each file has 8,760 rows and 31 columns, in MW.
- 32 province-aggregated 31×31 transmission-capacity matrices, one for each year/TL setting. No individual-line list is included.
- The 288-profile registry, 4,608 annual task definitions and 31 calibrated provincial thermal-capacity targets.
- `model/pcv3_build_lp.m`, the unchanged archived LP constructor; `model/run_public_case.m`, the public numerical-input adapter; synthetic constructor checks.
- Non-plotting peak, factorial, matched-comparison and allocation-price calculation functions, accepting caller-supplied output tables.

Plant names, name crosswalks, exact plant coordinates, input workbook names, original row linkages, raw workbooks, solver logs and institution-specific licence settings are not distributed. Numeric IDs are year-scoped model records and are not permanent physical unit identities.

## Verification without a solver

Python 3.10+, NumPy and pandas are sufficient. Place the virtual environment and reports outside this repository.

```bash
python -m pip install -r requirements.txt
python -B -m unittest discover -s tests -v
python -B tools/verify_model_inputs.py --report ../model_inputs_check.json
```

This verifies scope, file hashes, input coverage, numeric schemas, provincial capacity reconciliation and the 31×31 matrices. It does not execute annual dispatch. Validation reports are not archived research output.

## MATLAB use

See `docs/RUN_MODEL.md`. MATLAB and a separately licensed Gurobi MATLAB interface are required. Neither proprietary software nor its licence files are distributed. The recorded research environment used MATLAB R2022b and Gurobi 11.0.3; this public input adapter has not yet been accepted by a full-size annual comparison.

The LP constructor is unchanged. The adapter's FIXED interface now uses a locally re-solved OBA reference through `FixedReferenceDir`, instead of reading an archived reference table. The annual allowance formula and objective constant are unchanged. This avoids distributing research outputs as hidden runtime inputs. Users must first solve and check the appropriate reference; the packaging tool never launches that calculation.

## Coverage versus reproduction claims

All 288 main configurations have numerical input coverage. The adapter also exposes selected Kappa, Gamma, signal-internalization, demand and demand-response options. It does not automatically reproduce every supplementary protocol, historical 35% replay or final manuscript figure. Non-plotting analysis functions expect the documented annual-table schema; the short per-run adapter summary is not silently treated as a complete analysis table.

An inputs-only GitHub release is distinct from the supporting data arrangement for the paper. Availability statements must identify the separate access route for any minimum dataset supporting reported results. This repository does not claim that the journal's complete sharing requirements are fulfilled by input provision alone.

## Licences and attribution

The software is distributed under the MIT licence in `LICENSE`. The processed numerical inputs in `data/` are distributed under CC BY 4.0, as specified in `DATA_LICENSE.md`. These licences do not relicense proprietary software or underlying third-party source materials; see `docs/THIRD_PARTY_NOTICES.md`. The confirmed creators, repository URL and version are recorded in `CITATION.cff` and `RELEASE_STATUS.json`.
