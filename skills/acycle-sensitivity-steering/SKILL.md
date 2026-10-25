---
name: acycle-sensitivity-steering
description: Turn user steering into traceable MATLAB reruns and compare sensitivity without overwriting the baseline.
---

Open the relevant baseline with `acycle_get_run`. Resolve phrases such as "the previous figure" or "the original result" from the actual conversation and saved run IDs; do not assume that the latest created run is always the requested baseline. Translate only the user's requested changes into parameters. For one or several changes use `acycle_rerun` with `run_id`, `parameter_patch`, and an explanatory `label`. For a one-parameter sweep use `acycle_sensitivity` with `run_id`, `parameter`, and `values`.

`acycle_rerun` preserves the frozen input, original operation (`analyze`, `swa`, `coco`, or `ecoco`), effective defaults and other settings. Omitted parameters stay fixed. Never route a COCO/eCOCO/SWA adjustment through `acycle_analyze`. The core rejects a direct call whose `parent_run_id` belongs to another operation, and rejects omitted settings that would reset the parent's method. A user-requested change to a different operation starts a new independent analysis with its matching tool; compare its run ID with the original instead of assigning a false same-method parent.

Keep `method`, target definition, seed, correlation and units unless the user explicitly changes them. `parameter_patch` may use null to remove an optional field or restore a MATLAB default, but `method` and `detrend` require an explicit valid choice and cannot be reset with null. Switching an astronomical target between age and periods replaces the other target; switching `span` and `detrend_window` replaces the other window definition. Switching to linear COCO/eCOCO detrending removes an inapplicable span/window. Read the returned `steering.removed_or_reset_parameters` and explain those consequences. An incompatible change must be resolved explicitly, not replaced with another method to obtain a successful run.

A typical detrending check is `parameter: span`, `values: [0.25, 0.35, 0.45]`. These are experiments, not an optimization objective for maximizing significance. Changes to sample spacing, filtering bands, evolutionary windows and age assumptions need a scientific reason and correct units.

Run every scientific branch in MATLAB. Keep the baseline's input, parameters and outputs immutable. Check matching input hashes, the preserved operation, and the child's `parent_run_id`. Retrieve the new run IDs and use `acycle_compare` with `run_ids`. Compare coordinate domains and units before comparing peaks. Python may assemble saved summaries; any newly computed scientific diagnostic or comparison figure belongs in MATLAB. Present the returned MATLAB figures and saved-file attachments when the client exposes them; a file path alone is not evidence that the chat UI displayed a figure.

Explain what changed, what remained stable and what depends on the chosen settings. Do not present the most favorable branch alone or hide failed branches. Keep selected and rejected alternatives in the run record so a later user can retrace the decision.

For requests beyond Acycle, prefer extending its MATLAB interface. Python can handle genuinely missing capabilities or temporary user-specific extensions, but label their provenance and return their numeric output to MATLAB for subsequent Acycle analysis and plotting.
