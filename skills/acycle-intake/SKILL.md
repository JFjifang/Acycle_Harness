---
name: acycle-intake
description: Establish a cyclostratigraphic dataset, coordinate units, scientific question and available MATLAB/Acycle backend before analysis.
---

Use `acycle_capabilities` to check the configured backend and `acycle_inspect` with the user's input path. Distinguish a depth series from an age series, identify the proxy and units, and preserve the original file. Establish whether the user wants exploratory periodicity, a specified hypothesis, or a chronology. Infer metadata from an accompanying paper or table before asking for missing information.

Numerical processing and plots must run in MATLAB. Python is for Harness integration, transport and metadata; never silently switch to a Python analytical fallback when MATLAB is missing. Report an unavailable backend precisely and keep the request ready to rerun.

Use the first two numeric columns only when their meaning is clear. Check duplicate coordinates, missing observations, sorting, irregular sampling and large gaps in the MATLAB result. Duplicate handling and interpolation change the effective dataset and must be visible in the report. Do not turn depth wavelengths into kyr without a stated rate or age-depth model.

For a runnable first pass, call `acycle_analyze` with explicit baseline parameters, a descriptive `label`, and the original `input_path`. Record the returned run ID, effective parameters, MATLAB/Acycle provenance and artifacts. If the requested feature is outside the bridged subset, say so and prefer a small MATLAB adapter to the installed Acycle routines.

Return a concise dataset summary, important assumptions, available analysis path, and the next scientific decision. Do not imply that basic file inspection constitutes numerical quality control or that a successful API call means an analysis succeeded.
