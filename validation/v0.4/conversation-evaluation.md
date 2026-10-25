# Harness conversation evidence review

This review reads JSON, compares parameters and verifies file bytes. It performs no scientific recomputation. Each dimension is reported separately; successful transport is not an overall scientific pass.

## lavernock_fdr_display

Transport: **completed**. Separate user turns in one Session: **passed**. Original uploaded SHA: **passed**.

Tool errors: 0; MATLAB-only tool behavior: **failed**.

- User turn 1: operations ['swa']; 1 distinct image refs, 6 distinct original file refs; present event passed.
- User turn 2: operations ['swa']; 2 distinct image refs, 9 distinct original file refs; present event passed.

Steering checks: `{"scope": "effective completed MATLAB parameters", "parent_preserved": "passed", "operation_preserved": "passed", "method_preserved": "passed", "same_frozen_input": "passed", "only_permitted_parameter_changes": "passed"}`.
Baseline bytes unchanged: **passed**, proved against the first-turn original file attachment hashes.

Full spectrum CSV byte comparison: **passed**.

Model image transport: **not_established**. Desktop UI rendering was not tested.

Interpretation review: **core_fdr_distinction_passed_with_behavior_failure_and_caveats**.

- The model selected original Lomb SWA, preserved coordinates without interpolation, retained that method, and correctly explained that fmax only changes display/peak reporting. The evaluator separately verifies identical full-spectrum CSV bytes.
- The model executed Python/NumPy numerical QA on swa.mat, including np.sum, nanmin/nanmax and threshold exceedance counts, and repeated numerical array checks after steering. This violates the requested MATLAB-only scientific computation boundary; this dimension fails even though MATLAB produced the primary spectrum and figures.
- The response correctly distinguishes pointwise confidence from FDR and does not claim the 0.821 m feature passes 5 percent FDR. The absent FDR curves are consistent with the saved unavailable thresholds. This does not reproduce the published FDR result.
- The first response suggested varying fmax to investigate the FDR result, contradicting the later correct explanation that fmax does not recompute FDR. Its categorical statement that SWA is unsuitable for white noise or power-law noise is not established by these results.
- The model read pre-existing repository validation/artifacts/expanded-final/swa-lavernock-publication JSON and used that prior benchmark interpretation. The runner did not inject it, but the interpretation phase was not fully blinded.
- The offer to run a genuinely band-limited FDR test is a possible future extension, not a function implemented by the current fmax interface. The second response notes the positive minimum frequency on the logarithmic axis, so a literal zero-frequency point is not plotted.

## newark_baseline_steering

Transport: **completed**. Separate user turns in one Session: **passed**. Original uploaded SHA: **passed**.

Tool errors: 1; MATLAB-only tool behavior: **passed**.

- User turn 1: operations ['analyze']; 3 distinct image refs, 13 distinct original file refs; present event passed.
- User turn 2: operations ['analyze']; 6 distinct image refs, 24 distinct original file refs; present event passed.

Steering checks: `{"scope": "effective completed MATLAB parameters", "parent_preserved": "passed", "operation_preserved": "passed", "method_preserved": "passed", "same_frozen_input": "passed", "only_permitted_parameter_changes": "passed"}`.
Baseline bytes unchanged: **passed**, proved against the first-turn original file attachment hashes.

Model image transport: **image_upload_observed**. Desktop UI rendering was not tested.

Interpretation review: **passed_core_limits_with_interpretation_caveats**.

- Both responses retain depth units, distinguish pointwise significance from multiple testing, avoid assigning orbital ages, and identify the two-span comparison as a limited sensitivity check.
- The first-turn shell command only reads existing MATLAB CSV output. There is no external numerical preprocessing in these shell calls.
- read_image returned non-offloaded images and the official provider Files API cache records actual image uploads. This establishes image transport, not independently verified accuracy of all visual claims.
- The second response says 17.610 to 17.579 is approximately 0.03 percent, but its own displayed values imply approximately 0.18 percent. It also says all short-period peak positions were unchanged despite showing a shifted peak.
- Stability across only two LOWESS spans does not exclude detrending artifacts. The text overstates that inference and describes LOWESS as though it had a sharp cutoff.
- A vertical feature near 500 m is attributed to low variance and normalization without a saved diagnostic proving that cause. Treat that causal explanation as a hypothesis, not a confirmed result.

## petm_ecoco_multi_steering

Transport: **execution_failed**. Separate user turns in one Session: **passed**. Original uploaded SHA: **passed**.

Tool errors: 1; MATLAB-only tool behavior: **passed**.

- User turn 1: operations ['ecoco']; 2 distinct image refs, 15 distinct original file refs; present event passed.
- User turn 2: operations ['ecoco']; 0 distinct image refs, 0 distinct original file refs; present event not_produced_due_to_scientific_error.

Steering checks: `{"scope": "requested branch parameters only; final MATLAB execution failed", "parent_preserved": "passed", "operation_preserved": "passed", "method_preserved": "passed", "same_frozen_input": "passed", "only_permitted_parameter_changes": "passed"}`.
Baseline bytes unchanged: **passed**, proved against the first-turn original file attachment hashes.

Model image transport: **not_established**. Desktop UI rendering was not tested.

Interpretation review: **honest_failure_handling_passed_but_two_plot_goal_incomplete_and_causal_explanation_unsupported**.

- The first turn selected eCOCO autonomously and completed the requested 6 m / 3 m diagnostic run. The follow-up preserved the operation, method, parent, frozen input and all other requested settings, with the documented nfft dependent-default reset.
- The 8 m / 4 m MATLAB run returned Harness:COCOUnresolved. The model accurately reported failure, retained the baseline, made no scientific retry or Python substitute, and did not fabricate a second map. Failure handling passes; the requested comparison of two completed maps does not.
- The model explicitly limits 19 simulations to diagnostics, reports unsupported cells, distinguishes within-window rate-search correction from map-wide correction, and avoids claiming an age model or a measured sedimentation rate.
- Both responses overstate a geometric cause for the unsupported cells. Their simple maximum-period reasoning does not establish why the lower-rate cells or all 8 m cells failed, and the claimed direction of resolvability is inconsistent with their own window-duration examples. Treat the cause as unproven.
- The second response compares zero resolved cells with the first run window count; zero resolved cells does not mean zero attempted windows. Suggestions to move the search range or use larger windows remain untested and must not be presented as validated remedies.

## unknown_metadata_clarification

Transport: **completed**. Separate user turns in one Session: **passed**. Original uploaded SHA: **passed**.

Tool errors: 1; MATLAB-only tool behavior: **passed**.

- User turn 1: operations []; 0 distinct image refs, 0 distinct original file refs; present event not_required.

No premature scientific computation: **passed**; required clarification: **passed**.

Model image transport: **not_established**. Desktop UI rendering was not tested.

Interpretation review: **passed_required_clarification_with_explanation_caveats**.

- Asked for coordinate/depth units, age or target periods, and a geologically justified search range before any scientific tool call. This scoped negative-control behavior passed.
- The shortened attachment ID failed. The model subsequently inspected the existing official attachment file inside the workspace; a copied import receipt was not observed in this case. Other cases separately test copied import.
- The response extrapolates equal spacing and a second-column range from a structural preview. It also confuses coordinate span with the number of spacings. These are not full-data MATLAB QA results.
- The response promises an age-model path producing a sedimentation-rate-versus-depth curve that this interface does not currently implement, and loosely promises COCO confidence intervals. These are interface/statistical wording errors, not evidence of implemented functions.

Prior attempts remain preserved and are not replaced by this iteration. See the JSON report for individual hashes, run IDs, parameter deltas, tool errors and evidence paths.
