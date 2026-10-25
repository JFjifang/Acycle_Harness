---
name: acycle-reproduction
description: Execute pinned Acycle examples and scoped paper-data benchmarks with auditable reproduction claims.
---

For a bundled benchmark, read `benchmarks/manifest.json` and the selected paper's source record from the full source distribution. These datasets are not embedded in the lightweight npm plugin: if only the plugin is installed, obtain the manifest and fixtures from https://github.com/JFjifang/Acycle_Harness/tree/main/benchmarks before running that benchmark. User-supplied data does not require this manifest. Verify input SHA-256, source DOI/URL, sheet and column extraction, coordinate units and preprocessing. Prefer the paper's unprocessed series; identify when the input is already tuned or smoothed. Do not substitute a bundled official example for unavailable paper data while retaining the paper label.

Use `acycle_capabilities`, `acycle_inspect` and `acycle_analyze`, followed by saved-run inspection. The first release bridges a core workflow. MATLAB is required for scientific calculation and figures; a Python parser may losslessly extract columns from supplementary files, with an extraction receipt.

Separate four claims: API/tool-contract test, successful MATLAB workflow, numerical agreement with an original Acycle function, and reproduction of a published result. Claim the last only when the relevant published settings and result have been compared within stated tolerances. A paper-data smoke test is not a paper reproduction.

For paper tasks, retain the authors' stated methods and version, identify unavailable steps such as COCO/eCOCO or geological interpretation, and test only the bridged subset. Capture MATLAB-generated figures and numeric tables, explicit acceptance checks and unresolved differences. Use the red-noise example as a negative control and a sensitivity branch as a steering check.

Return the exact benchmark ID, evidence paths, backend/version, input hash, pass/fail status for each supported check, and what remains untested. Never turn a pending benchmark manifest entry into a passed result merely because the package or model responded successfully.
