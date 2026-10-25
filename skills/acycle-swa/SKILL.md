---
name: acycle-swa
description: Run Acycle Smoothed Window Averages and its FDR treatment in original MATLAB code, preserving uneven sampling where supported.
---

Use this skill for SWA (Smoothed Window Averages, 平滑窗口平均), not wavelet analysis or spectral weighted averaging. Start with `acycle_capabilities` and `acycle_inspect`; scientific checks and all numerical processing belong to MATLAB. Call `acycle_swa` with `input_path`, `parameters`, optional `label` and `parent_run_id`. Follow the live schema rather than inventing parameter names.

Choose `method: lomb` for the original Lomb–Scargle/SWA/FDR path, including irregularly sampled data. It retains original sampling and the upstream routine's internal detrending, taper and Hanning operations. Do not pre-interpolate solely to make the data look regular, or pass MTM-only `mtm_nw`, `pad_factor`, `detrend` parameters to this path. `method: mtm` uses original MTM/SWA/FDR routines and requires a uniformly sampled input; explicit MTM settings must be saved with the run. Both paths require at least 66 valid observations, and the older original Lomb code may have additional short-record window limitations that must be reported honestly.

State coordinate units. Read the returned effective parameters, original-source hashes, confidence/FDR columns and MATLAB figures. SWA confidence levels and its FDR treatment are different from the mini-robot robust AR(1) curve: identify which method was used. Original missing FDR thresholds may mean no independent rejection threshold or a merged threshold; NaN/null is not a zero threshold. Do not fill these cells with guessed values.

If a user changes method, taper-related assumptions, detrending or frequency display limits, preserve the baseline and record an independent run. Numerical values and figures must remain MATLAB outputs; no Python replacement after an original algorithm fails. An implementation limitation or changed upstream source is not evidence that the hypothesis failed.

For paper verification use the exact dataset, sample coordinates, published preprocessing and stated spectral settings. Distinguish direct-original parity, recovery of a reported band/threshold and reproduction of a full chronology. Open at least the spectral figure and retain CSV, MAT, PNG and FIG artifacts. Explain which peaks survive the specified method's FDR procedure and which remain exploratory; neither establishes orbital forcing by itself.
