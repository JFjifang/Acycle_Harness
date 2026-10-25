---
name: acycle-spectral-interpretation
description: Assess Acycle MATLAB spectra and filtering results without overstating significance or orbital attribution.
---

Read the saved MATLAB result using `acycle_get_run`. Check detrending, interpolation interval, time-bandwidth product, spectral smoothing, spectral resolution and coordinate units before interpreting peaks. Use `acycle_analyze` for a changed parameter set, preserving `parent_run_id` and assigning a new label.

Confidence curves are pointwise relative to their stated background model. Searching many frequencies, windows or parameter settings increases false-positive opportunities. Neither a threshold crossing nor a filtered oscillation alone demonstrates astronomical forcing. Explicitly distinguish observation, hypothesis and independent corroboration.

For a user-selected band, pass `filter_band: [low, high]` in reciprocal coordinate units and a supported `filter_method` (`gaussian` or `taner_hilbert`). Validate that the requested range lies within available frequencies. MATLAB must compute filtering, Hilbert envelopes and figures. Record the chosen band before comparing its output with orbital periods; do not select and confirm a band on the same evidence without acknowledging selection.

Compare peaks and evolutionary persistence across reasonable detrending or sampling settings with `acycle_sensitivity` and `acycle_compare`. Run the official red-noise control when validating a workflow. Explain that random noise can still exhibit pointwise exceedances; the negative control is not required to have zero peaks.

If the requested significance test is unavailable, state that limitation. A new method may be added as a clearly labeled extension, preferably MATLAB, with the model and assumptions retained. Do not rename an approximation as Acycle's original test.
