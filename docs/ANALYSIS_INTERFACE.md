# Non-plotting scientific calculations

This folder retains calculation methods, not drawing/layout scripts or stored study outputs. `national_metrics.py` preserves peak classification, full-factorial decomposition and strict CQ contrasts from the prior release code. `gamma_metrics.py` and `common.py` are unchanged scientific calculation code.

```bash
python analysis/analyze_generated.py national --input /external/path/national.csv --out /external/path/new_national_metrics
python analysis/analyze_generated.py gamma --input /external/path/path_years.csv --out /external/path/new_gamma_metrics
```

National input is a single treatment's 4,608-row table with profile_id, year, the six factor columns, emissions_t, reported_generation_cost_cny, average_generation_cost_cny_per_mwh, coal_mwh, gas_mwh, wind_mwh, solar_mwh and hydro_mwh. Repeated 16-year rows must retain the same profile factors. Do not mix Kappa treatments in this input.

Gamma input is the 192-cell table for profiles 15 and 42, OBA/FIXED, nominal gamma 1/5/10, 2020–2035, containing profile_id, year, path_nominal_allocation, path_nominal_gamma and the quantities in `gamma_metrics.METRICS`. This includes physical generation, carbon balances, costs and curtailment. It is a caller-generated numerical table, not a file distributed here.

The short summary written by a single run_public_case call does not automatically have every field of these analysis schemas. Users must construct the required annual aggregates with the same definitions. This release preserves the calculations without claiming a new full-output aggregation bridge or automatically reproduced published figures.
