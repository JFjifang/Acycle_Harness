---
name: acycle-astronomical-tuning
description: Build transparent relative astronomical control points from MATLAB bandpass peaks and troughs, then diagnose the original proxy in time.
---

Use `acycle_tune` on a saved MATLAB `filtered_csv` (coordinate, filtered signal, optional envelope) or a two-column bandpassed curve. Read the filter run and inspect its plotted curve first. Establish the depth unit, filtering band, target full-cycle period in kyr, selected extrema, and age convention. Do not invent an absolute age anchor from a spectral peak.

Require explicit `period_kyr`, `anchor_age_kyr`, `anchor_phase` (`peak` or `trough`), `extrema` (`peaks`, `troughs`, or `both`), and `depth_unit`. The original Acycle `getpks` identifies extrema without an invented Python peak detector. Same-phase controls advance a full period; alternating peaks and troughs advance half periods. The first selected anchor-phase extremum receives the anchor age, so a preceding opposite-phase control can have a negative relative time. Flat/ambiguous extrema and failure to alternate require inspection, not silent point removal. These automatically proposed controls are a hypothesis and need geological review.

Default `endpoint_policy=trim` keeps the control-point-covered interval. `linear_extrapolate` explicitly extends endpoint slopes and must be disclosed. `error` rejects uncovered samples. Examine `control_points_csv`, `age_model_csv`, the three-panel diagnostic, sedimentation-rate behavior and discarded endpoints. All numerical conversion and plots are MATLAB, using original `depthtotime`.

For the time-domain diagnostic call `acycle_analyze` with the ORIGINAL proxy input and `tuning_run_id` pointing to the completed tuning run. This applies its saved MATLAB age model and covered coordinate range, with artifact hash verification. Do not diagnose only `tuned_csv` and use its imposed period as proof. Specify output `coordinate_unit=kyr`, a justified time sampling interval, and time-domain evolutionary windows. Interpolation spacing is not independent temporal resolution.

Present the selected band, period, phase, relative/absolute anchor and boundary policy alongside the result. Orbital agreement caused by tuning is conditional; independent ages, untuned bands, alternate controls and sensitivity checks are needed for a stronger chronology claim. Rerunning tuning creates a new model; rerun the original proxy with that new `tuning_run_id` to update the time diagnostic.

Source/provenance: `docs/INTERPOLATION_TUNING_SOURCES.md` and `matlab/preparation_sources.json`. Do not conflate this extrema-based bridge with the entire interactive Acycle astronomical tuning GUI or a validated automatic age model.
