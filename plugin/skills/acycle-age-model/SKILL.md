---
name: acycle-age-model
description: Apply explicit sedimentation-rate or age-depth assumptions through MATLAB while preserving stratigraphic uncertainty.
---

Establish depth direction, depth units, age convention and independent age constraints. Do not infer absolute ages from a spectral peak. Read the baseline with `acycle_get_run` and create a new analysis with `parent_run_id`.

For a constant-rate experiment use `sedimentation_rate` in cm/kyr, `depth_unit` (`m`, `dm`, `cm`, `mm`, `ft`, or `km`) and `first_age_kyr`. For explicit tie points use `age_model: [[depth, age_kyr], ...]`. These are supplied assumptions; the adapter does not discover a validated astronomical chronology. Never supply a rate and tie-point model as competing hidden assumptions. MATLAB performs conversion and subsequent analysis.

Verify that tie points are ordered consistently and the data are covered; inspect the effective behavior at boundaries. Flag hiatuses, reversals or nonmonotonic models instead of interpolating through them without explanation. Label outputs as age-domain or depth-domain and retain the original series and model.

Compare plausible rates or alternative tie points as separate runs. State how candidate periods move with the model. Agreement created by orbital tuning is not independent proof of the tuning target. A chronology claim needs independently justified tie points, uncertainty and stratigraphic checks.

For bandpassed extrema-derived controls, load `acycle-astronomical-tuning` and use `acycle_tune`. For a saved tuning run, pass `tuning_run_id` to `acycle_analyze` on the original proxy; this checks the saved control-point artifact, applies the MATLAB age model, and restricts analysis to its covered interval. General interactive GUI tuning, automated control editing and uncertainty propagation are not implemented by this bridge. Check `acycle_capabilities` before promising additional functions; do not substitute an unrelated Python calculation under an Acycle label.
