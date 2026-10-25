---
name: acycle-interpolation-pro
description: Use Acycle Interpolation Pro in MATLAB with explicit method, grid, gap and endpoint choices.
---

Use `acycle_interpolate_pro` for a separately inspectable preprocessing run. Input is a numeric two-column coordinate/proxy file. Establish coordinate units and sample spacing first; interpolation does not create new independent observations or recover unresolved frequencies.

The MATLAB adapter extracts the numerical callback from Acycle `interpolationGUI.m`: `linear`, `nearest`, `next`, `previous`, `pchip`, `cubic`, `v5cubic`, `makima`, and `spline`. Choose a defensible method, normally linear for first exploration; use pchip when shape preservation is relevant. Explicit `dt` is in the coordinate unit. Omitted `dt` follows the original GUI median-spacing default.

`gap_policy=interpolate` is the GUI default. `gap_policy=zero` reproduces the GUI zero fill beyond `dt * gap_multiplier`, default multiplier 10; zero-filled gaps can produce spectral artifacts and are not observations. Inspect the gap report and figure. Do not silently zero-fill a hiatus. The `gui` endpoint policy preserves the original colon grid and its two-endpoint fallback when requested spacing exceeds the entire span; `strict_grid` rejects that fallback. Neither silently appends an off-grid final point.

Pass the saved `interpolated_csv` to subsequent MATLAB tools when regular sampling is wanted; keep the input receipt and preprocessing run ID. Do not reimplement interpolation or gap diagnosis in Python. Change a single option using `acycle_rerun`, preserving other settings. Report both requested and actual spacing and the resulting sample count.

Source/provenance: `docs/INTERPOLATION_TUNING_SOURCES.md` and `matlab/preparation_sources.json`. A passed bridge test establishes parity with the extracted original calculation, not validity of a particular geological interpolation choice.
