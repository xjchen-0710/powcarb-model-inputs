# Numerical input definitions

Thermal file identity is `(year, CQ, COP)`. Fields are:

| Field | Meaning and units |
|---|---|
| unit_id | Year-scoped numerical ID, e.g. Y2020U0001; no real-world name linkage |
| year, record_id, province_id | Model year, contiguous record number, province 1–31 |
| is_gas | 1 gas, 0 coal-category record |
| capacity_mw | Province-calibrated capacity weight in MW, not a newly measured nameplate |
| fuel_kg_per_mwh | Fuel-use coefficient |
| fuel_cny_per_mwh | Marginal fuel cost, CNY/MWh |
| emissions_t_per_mwh | Direct generation emissions, t CO2/MWh |
| quota_t_per_mwh | Applicable output-linked free-allowance intensity, t CO2/MWh |

All 192 tables have been selected as coefficients from the frozen source input representation. Although their earlier export used accepted-case files as a convenient carrier, no generation, annual emissions, annual cost or realized allowance quantities are included. The supplied coefficients are inputs; they are not optimization outcomes.

`data/model_inputs/hourly/YYYY_REn_resource.csv.gz` contains 8,760 rows and columns P01–P31. Wind/solar/hydro are available generation bounds, nuclear is prescribed and COMMON load is demand. Arrays are MW over 1-hour intervals, not simulated output. The model uses 8,760 hours in every year; no leap-day multiplier is added.

Province labels P01–P31 match `data/scenarios/reference_capacity_2020.csv`. `capacity_mw/YYYY_TLn.csv` has a numeric 31×31 block plus row and column labels. The matrix is symmetric with a zero diagonal. Each positive pair is one aggregated bidirectional corridor. Count capacity once using one triangle. Effective year/TL limits already include the specified transmission multiplier; the public adapter must not apply it again. No realized electricity-flow NPZ is included.

The full factorial registry varies RE(2), CF(3), TL(2), CQ(6), CAP(2), COP(2), jointly 288 configurations. The task table provides year-specific prices and settings. Historical Chinese strings in its scenario-label columns are policy labels, not plant names. `reference_profile` in export indexes is a numerical bookkeeping identifier for the input source, not an outcome or facility identity.

The signed national net allowance deficit is emissions minus free allowances. The net carbon cost is pD + (kappa−1)p max(D,0); CQ1 disables it. Gamma scales the price only from 2023. The physical objective includes linear supply/demand slack penalties. Reported generation-side cost excludes those penalties and adds fixed thermal O&M at 308845 CNY/MW/year. These definitions are not social-welfare accounts.
