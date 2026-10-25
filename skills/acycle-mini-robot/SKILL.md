---
name: acycle-mini-robot
description: Run the supported headless subset of Acycle mini robot with original MATLAB routines and inspect saved outputs.
---

Start from `acycle-intake`. Call `acycle_analyze` with `input_path`, optional `label`, and `parameters`. Baseline parameters are `detrend: lowess`, `span: 0.35`, `mtm_nw: 2`, and `evolution: true`; inspect the returned effective values for interpolation, frequency extent, smoothing and evolutionary window. These choices follow the pinned master workflow, not every historical Wiki setting.

MATLAB performs cleaning, interpolation, detrending, spectral calculation, evolutionary analysis and plotting. Prefer direct Acycle functions; GUI extractions require source attribution. Do not reproduce these numerical steps in Python. Store MATLAB-generated processed data, spectral tables and figures alongside the run response.

Inspect the original/processed series, trend, power spectrum, red-noise curves and evolutionary plot. Check coordinate units and confirm the frequency axis is reciprocal to those units. Flag broad trends, gaps, boundary effects, short windows and peaks close to Nyquist. Treat any listed strongest peaks as exploratory candidates, not automatic orbital identifications.

Use `acycle_get_run` to reopen saved results. If a computation fails, report its failed stage and dependency; never supply a Python substitute under the same run identity. Successful execution is distinct from direct-call parity and from scientific validation of an interpretation.

For follow-up requests use `acycle_rerun` with the selected baseline and only the requested parameter patch, or `acycle_sensitivity` for a one-parameter sweep. Preserve the baseline's method and data, retain the new parent link, and compare saved runs. Do not reconstruct the whole parameter set from memory or drop previously selected options.

Deliver the run ID, supported workflow executed, key artifacts, two or three observations, and limitations relevant to the user's question.
