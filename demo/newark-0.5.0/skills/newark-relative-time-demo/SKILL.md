---
name: newark-relative-time-demo
description: Run the explicitly selected Newark relative-time demonstration using its public scientific assumptions and original Acycle MATLAB routines; do not apply these priors to ordinary datasets.
---

Use this skill only when the user explicitly chooses the Newark demonstration and supplies the corresponding official example file. This is a workflow-guided demonstration, not unrestricted blind method selection. Locate and read the adjacent demo package's `manifest.json` and `SOURCES.md`; the manifest is two directories above this skill directory. Verify that the imported/workspace input hash matches the manifest. If another file is supplied, establish its scientific context rather than applying Newark parameters.

Tell the user briefly that you are using the public demonstration assumptions: a 405-kyr relative chronology, 210 Ma only for approximate orbital target periods, and 19 simulations for quick exploration. Loading this named demonstration constitutes permission to use its declared priors; no repeated confirmation is needed. If the user changes the study assumptions, preserve the earlier version and make the change explicit.

Use the installed Acycle intake, mini-robot, COCO, age-model and sensitivity skills together with the current tool schemas. Inspect supported capabilities. Import the current authorized attachment using the host bridge, or use its exact workspace path. Preserve raw bytes and source attribution. Every numerical operation, extrema selection, interpolation, tuning and figure must execute in MATLAB using Acycle sources. Python may transport files, coordinate requests and present artifacts. Do not use Python/NumPy to derive numeric QA, spectral results, control points or charts.

Follow the public research sequence, retaining the manifest settings unless the user requests a change:

1. Establish input units and numerical quality in MATLAB through original Acycle Interpolation Pro, using the manifest's interpolation preset. Retain the original input and the actual `interpolated_csv` output, grid/gap diagnostic and source linkage. Do not replace the 0.85344-m example grid with the differently sourced 0.85-m grid.
2. Run original Acycle preprocessing, depth-domain MTM and EvoFFT on that Interpolation Pro artifact with the manifest's depth preset. The depth analysis may also generate the declared Gaussian filtered artifact in the same MATLAB pass; reuse that actual output to avoid redundant computation.
3. Run full-record COCO and complete-window eCOCO on the same Interpolation Pro artifact with the manifest presets. Keep the 5–25 cm/kyr grid, resolved-period counts, NaN cells and original Monte Carlo outputs. The period/age prior is supplied context, never a number inferred from the strongest observed peak.
4. Use the actual MATLAB filtered file as input to the supported tuning operation. Extract maxima in MATLAB; assign the first selected maximum relative time zero and consecutive maxima 405-kyr spacing. Keep the manifest's trim policy. Use Acycle tuning/interpolation and retain the controls, selected extrema, full provenance and age-depth figure. If extrema are insufficient or controls are invalid, report that stage instead of inventing a usable chronology.
5. Analyse the original raw proxy in relative time through the completed tuning run's controls, using the supported `tuning_run_id` linkage and manifest time-diagnostic preset. Do not feed the narrow-band filtered output to this diagnostic. Respect the trimmed control range and report the actual regridding used. The raw source hash differs from the formatted Interpolation Pro output hash; preserve both and their lineage.
6. Return key original MATLAB images, downloadable source artifacts and a short interpretation. Mark the chronology “405 kyr假设下的相对时间轴”. Include no more than a few main observations in the conversation; preserve tables and technical provenance in artifacts.

Use live, newly completed outputs. Reopening a saved run is allowed when explicitly presenting that saved result; label its origin. Never replace a failed live calculation with a successful rehearsal result, hide a parameter search, silently substitute another method, or convert this scenario's deliverable list into a claim that all stages passed.

Interpretation requirements:

- A depth spectrum peak is an exploratory candidate. Do not assign astronomical names by appearance alone.
- The 60-m centre is a sourced regional prior; the 48–80 m nominal bandwidth is an explicit demo choice. It was not chosen by matching this run's strongest peak.
- Use rate-global COCO Monte Carlo results. eCOCO's global correction applies within each window, not across the full map. With 19 simulations, do not claim p < 0.05.
- Inspect target resolution at candidate rates; retain unresolved cells and multiple candidate ridges. An all-NaN map is an unresolved stage, not evidence of no orbital forcing and not permission to search silently for a pleasing map.
- A 405-kyr time-spectrum peak is partly imposed by the tuning hypothesis. Other time-domain peaks also depend on this model; neither supplies independent absolute dating.
- Peak/trough selection is a phase convention. The first control's relative zero is not an absolute age. No formal age uncertainty model is provided.
- EvoFFT's zero-padded edges and eCOCO's unpadded complete windows have different support. Do not interpret map edges as equally constrained.

For a follow-up, use saved-run steering where supported and change only requested parameters. In particular, an eCOCO window/step change remains the original eCOCO method. A tuning-phase change starts from the same filtered file, retains period and endpoint policy, creates new controls and then reapplies them to the original proxy. A depth-only detrending request does not authorize quietly rebuilding all derived chronologies. Keep parent links, input hashes and actual effective parameters. Compare before and after using saved MATLAB results.

Do not promise a 3–5-minute live completion time. That interval is a possible speaking plan; execution time depends on the actual backend and client. Numerical completion, artifact delivery and pixels rendered in the user's client are separate observations.
