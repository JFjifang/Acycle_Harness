---
name: acycle-sensitivity-steering
description: Turn user steering into traceable MATLAB reruns and compare sensitivity without overwriting the baseline.
---

Open the baseline with `acycle_get_run`. Translate the user's requested change into explicit parameters and preserve everything else. For one parameter use `acycle_sensitivity` with `run_id`, `parameter`, and `values`; for a more complex branch use `acycle_analyze` with `parent_run_id` and an explanatory `label`.

A typical detrending check is `parameter: span`, `values: [0.25, 0.35, 0.45]`. These are experiments, not an optimization objective for maximizing significance. Changes to sample spacing, filtering bands, evolutionary windows and age assumptions need a scientific reason and correct units.

Run every scientific branch in MATLAB. Keep the baseline's input, parameters and outputs immutable. Retrieve the new run IDs and use `acycle_compare` with `run_ids`. Compare coordinate domains and units before comparing peaks. Python may assemble saved summaries; any newly computed scientific diagnostic or comparison figure belongs in MATLAB.

Explain what changed, what remained stable and what depends on the chosen settings. Do not present the most favorable branch alone or hide failed branches. Keep selected and rejected alternatives in the run record so a later user can retrace the decision.

For requests beyond Acycle, prefer extending its MATLAB interface. Python can handle genuinely missing capabilities or temporary user-specific extensions, but label their provenance and return their numeric output to MATLAB for subsequent Acycle analysis and plotting.
