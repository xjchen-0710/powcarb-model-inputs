# Public model interface

The repository packaging and Python input verification never launch MATLAB or Gurobi. The commands below are for a future model execution on a machine with adequate resources and a valid Gurobi MATLAB installation. Paths are examples to be replaced with the user's own paths.

```matlab
repo = '/absolute/path/to/powcarb_model_inputs_public_r1';
addpath(fullfile(repo, 'model'));
selftest_constructor();  % synthetic constructor only, no Gurobi call
```

One annual OBA run:

```matlab
refOut = '/absolute/path/outside_repo/P015_2035_OBA_g1';
run_public_case(repo, 15, 2035, refOut, ...
    'Kappa', 1, 'Gamma', 1, 'Allocation', 'OBA');
```

The output directory must not already exist. An accepted run produces a summary, numerical unit-generation table, numerical dispatch MAT, run settings and a completion marker. These newly computed files are generated locally and are not part of the input release.

FIXED without archived result files:

```matlab
fixedOut = '/absolute/path/outside_repo/P015_2035_FIXED_g10';
run_public_case(repo, 15, 2035, fixedOut, ...
    'Kappa', 1, 'Gamma', 10, 'Allocation', 'FIXED', ...
    'FixedReferenceDir', refOut);
```

For years from 2023, FIXED requires an accepted reference from this adapter for the same profile and year, OBA, Gamma=1, Kappa=1 and Alpha=1, with the same DemandScale and DRFraction. Fixed annual allowance equals the sum of the current unit quota coefficients times reference annual generation. The reference table is created by the user's preceding solve; it is **not** bundled as a published simulation outcome. For years before 2023, the interface uses the common OBA/reference-price formulation, consistent with its original API convention.

The loader verifies reference record IDs, provincial membership, capacities and coefficients, recorded treatment settings and input-bank identity. It retains the constant allowance credit in the fixed-allocation objective and reported carbon account. OBA and FIXED are not synonymous with turning free allocation on and off.

There is no blanket full-size acceptance claim. The constructor is preserved byte-for-byte, but the public loader and this local-reference interface still require runtime acceptance on the authors' or users' licensed environment. The material is not an end-to-end launcher for every supplementary experiment. Do not extrapolate a two-hour constructor check to an accepted national annual optimum.
