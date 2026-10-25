# SWA: Smoothed Window Averages

SWA means **Smoothed Window Averages**, or 平滑窗口平均. The bridge invokes the MATLAB implementations distributed with Acycle; it does not reproduce the method in Python. The numerical source reference is Acycle commit `dcba4279168745b563e0535b954297023dd62fc7`. `matlab/swa_sources.json` records the original files and hashes; each result records actual hashes, MATLAB/toolbox versions and the adapter hash.

## Two explicit methods

`method: "lomb"` is the default and follows the dedicated Acycle `SWAgui.m` path into `code/package/swa/specswafdr.m`. That original routine performs linear detrending, a split cosine taper at both 5% ends, the Lomb–Scargle transform and three Hanning smoothings. It fits the SWA background and computes both pointwise chi-square and false-discovery-rate thresholds. It preserves irregularly sampled coordinates: **do not interpolate or gap-fill this input**. Parameters for LOWESS, interpolation, MTM bandwidth or zero padding are deliberately not accepted by this method. The separate Bayesian spectrum shown by the full Acycle GUI is outside this bridge.

`method: "mtm"` calls original `code/package/swa/spectralswafdr.m` with its MTM option, which invokes original `specswa.m` for the background. This requires uniformly sampled coordinates. The wrapper permits mean removal (default), linear detrending, or `none`; all run in MATLAB. It never silently interpolates an irregular record. If scientifically warranted, explicitly prepare a uniform series first and pass the resulting file into the SWA tool. MTM SWA and the default Lomb SWA differ in periodogram, smoothing and degrees of freedom; they are separate analysis choices, not numerical substitutes.

Parameters accepted by both methods:

| Parameter | Meaning |
| --- | --- |
| `method` | `lomb` (default) or `mtm` |
| `coordinate_unit` | Label for the coordinate, e.g. `m` or `kyr`; it does not convert units |
| `fmax` | Optional display/peak-report upper frequency; the fitted full spectrum and FDR calculation remain unchanged |

Additional MTM-only parameters:

| Parameter | Default and meaning |
| --- | --- |
| `mtm_nw` | 2; time-halfbandwidth, range 1–8 |
| `pad_factor` | 1; original routine rounds this times the row count to obtain NFFT; range 1–10 |
| `detrend` | `mean`; alternatives `linear`, `none` |

Both paths require at least 66 finite observations and unique coordinates. The wrapper sorts observations and removes non-finite rows, recording the count; duplicate positions must be resolved explicitly. A gap exceeding 30% of the full span is rejected. The original legacy Lomb implementation can still fail when a short record cannot support its candidate background windows. That original error is reported; the wrapper does not silently change to MTM or replace its algorithm.

## Outputs and interpretation

All outputs are generated in MATLAB: cleaned and prepared CSVs, a 13-column spectrum CSV with explicit column names, `swa.mat`, a PNG and editable FIG, provenance JSON, and the original Acycle DAT files. Fixed-name files emitted by the original functions are contained in the new run directory. The adapter restores the caller's working directory, search path, figure visibility and the base-workspace variables overwritten by `specswafdr`.

`swa-prepared.csv` is the exact array passed to the original entry point. For Lomb this is the sorted finite input, because detrending and tapering take place inside `specswafdr`; it must not be described as an exported internally tapered series. For MTM it includes the explicitly selected wrapper detrending.

Spectrum columns are frequency, power, SWA background; 90%, 95%, 99%, 99.9%, 99.99% pointwise chi-square levels; and 10%, 5%, 1%, 0.1%, 0.01% FDR levels. Acycle may return an all-NaN FDR column when no independent threshold is emitted, including coincident threshold levels. This is preserved, marked unavailable in metadata and omitted from the plot. Do not interpret it as a zero threshold or a p-value. Counts in `fdr_exceeding_frequency_bins` count ordinates, not independent peaks; unavailable values are JSON `null`.

SWA was designed for red-noise backgrounds without prior high-pass filtering. Its assumptions do not generally cover white noise, power-law noise, arbitrary variance nonstationarity or strongly aliased sampling. Pointwise confidence is not FDR control; FDR control is conditional on the model and does not itself establish orbital forcing. Changing the method, interval or preprocessing creates a new analysis choice that should remain visible in a sensitivity record.

## Validation targets

The suite compares the MTM bridge with direct original `spectralswafdr` on the complete bundled Newark depth-rank example. It separately compares the default Lomb bridge with direct original `specswafdr` on the Lavernock 0–13.17 m record used by Weedon (2020), checking the published approximately 0.81 m wavelength against the original 5% FDR output. These are executable test targets; actual pass/fail outcomes come from the MATLAB validation receipt, not from this description. Only the specified spectrum is tested, not the paper's Bayesian analysis or its entire geological interpretation.

The method's original authorship and citation requirements are retained in the unmodified source checkout:

- Weedon, Page & Jenkyns (2019), *Cyclostratigraphy, stratigraphic gaps and the duration of the Hettangian (Jurassic): insights from the Blue Lias Formation of Southern Britain*, [Geological Magazine](https://doi.org/10.1017/S0016756818000808).
- Weedon (2020), *Confirmed detection of Palaeogene and Jurassic orbitally-forced sedimentary cycles in the depth domain using False Discovery Rates and Bayesian probability spectra*, [Boletín Geológico y Minero](https://doi.org/10.21701/bolgeomin.131.2.001).
- Weedon (2022), *Problems with the current practice of spectral analysis in cyclostratigraphy: avoiding false detection of regular cyclicity*, [Earth-Science Reviews](https://doi.org/10.1016/j.earscirev.2022.104261).

Original program: Graham P. Weedon. MATLAB translation and Acycle integration: Mingsong Li. The wrapper's plotting layer adapts `SWAgui.m` / `spectralswafdr.m` display conventions while plotting the original numerical arrays unchanged.
