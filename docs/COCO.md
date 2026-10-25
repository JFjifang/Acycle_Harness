# COCO and eCOCO: original MATLAB bridges

`acycle_coco` and `acycle_ecoco` use the same MATLAB batch entry as the other
tools. Python transports the input and JSON; computations, Monte Carlo draws,
tables, MAT files and PNG/FIG/PDF figures execute in MATLAB. The validated source
candidate is Acycle `dcba4279168745b563e0535b954297023dd62fc7`.

## Numerical and plotting methods

| Public operation/method | Original Acycle numerical function | Meaning |
| --- | --- | --- |
| COCO `adaptive` (default) | `corrcoefslices_rankNew`, target mode `adaptive9b` | Coherent nine-term target with four-group area/leakage amplitudes estimated separately for observed and null spectra |
| COCO `phase_averaged` | `corrcoefslices_rankNew`, target mode `adaptive` | Phase-averaged noncoherent target with per-orbit estimated amplitudes; supports the six-period PETM paper target |
| eCOCO `adaptive` (default) | `ecoco` → `ecocoAdaptiveCore` | Full-rate-grid sliding physical windows; coherent nine-term/four-group target |
| eCOCO `blocked` | `ecoco` → `ecocoCrossfitCore` | Bidirectional held-out windows with strict consensus, retaining unresolved edge cells |
| eCOCO `interleaved` | `ecoco` → `ecocoInterleavedCore` | Original odd/even split-before-interpolation window pipeline |

The public Acycle GUI currently defaults to Blocked cvCOCO. This initial full-record
bridge deliberately exposes the two named Adaptive methods above; it does not claim
to implement every GUI or historical COCO mode. `adaptive` means the current
coherent-nine selection, not the older internal function token `adaptive`.

COCO uses the original `cocoAdaptivePublicationReport` for its maximum-statistic
Monte Carlo audit and Wilson interval, and `plotAdaptiveCocoPublication` for both
rate curves and the null-maximum histogram. eCOCO uses the original `ecocoplot` for
the map overview and ridge-score figure. No numerical or plotting algorithms are
translated into Python. The only preprocessing callback extraction is documented
below. `matlab/coco_sources.json` contains hashes of the conservative original
dependency set, including background routines and orbital-resource tables. Each run
records actual source hashes, MATLAB release, adapter hash and input checksum.
The adapter makes two display-only adjustments to COCO figures: it expands the
four-panel figure to 1100 × 1000 pixels so probability ticks remain legible, and
replaces underscores in the method title with spaces to prevent TeX subscripts.
Original plotting functions, curves and axes are retained; eCOCO layout is unchanged.
Changed or removed snapshot files are recorded as source mismatches and produce
a warning. Required callable entrypoints are checked before execution; a new
Acycle revision is not labeled validated merely because it completes a run.

## Parameters and units

Require `depth_unit` (`m`, `cm`, `mm`, `dm`, `km`, `ft`), positive
`sedimentation_rate_min`, `sedimentation_rate_max`, and
`sedimentation_rate_step`, with rates in **cm/kyr**. Input coordinates, eCOCO
`window`, `step`, and optional `detrend_window` use the declared input depth unit.
The adapter converts depths to metres; original routines receive metres throughout.
All returned eCOCO depths and exported depth axes are metres. No geological age is
guessed from a filename.

Specify exactly one of:

- `middle_age_ma`: explicit geological age. Original `calculate_orbit9` rounds it
  to an integer Ma and uses its adjacent `AstroGeo22.txt` and `La04gisi.csv` resources.
  The wrapper converts its period column from years to kyr and records the rounded age.
- `orbital_periods_kyr`: explicit positive, distinct periods. Modern coherent COCO
  and all eCOCO modes require exactly nine; `phase_averaged` accepts 2–9 periods.
  The numerical core accepts more, but the original publication audit caps the
  participating-period count at nine, so this initial bridge rejects larger targets.

Other options are `nsim` (default 199, range 1–10000), `seed` (default 1),
`correlation` (`Spearman` default or `Pearson`), `red_noise` (0 no background-spectrum
subtraction, 1 classical
AR(1) subtraction, 2 robust AR(1) subtraction, 3 SWA subtraction), `nfft`, and
`max_frequency` in cycles/kyr. The latter defaults to 1.2 divided by the shortest
target period and must contain every target frequency. COCO additionally accepts
`slices` (default 1); eCOCO requires physical `window` and `step`.
COCO alone also accepts `dt`, in the input depth unit. This calls original Acycle
`interpolate` after optional LOWESS/LOESS and before the COCO core; merely passing
an interval to the modern core would not work because it recalculates median dt.
Omit `dt` for the original automatic median-spacing behavior. Explicit full-record
resampling is not exposed for eCOCO held-out modes.
`red_noise: 0` does **not** disable Monte Carlo testing; `nsim` controls the number
of null realizations independently of background-spectrum subtraction.

The adapter never pads eCOCO edges. It retains complete physical windows on the
requested step lattice; it does not append an off-step final window. Strict Blocked
consensus keeps unsupported cells as NaN in MAT/CSV and null in JSON. NaN is not
replaced with a significance value. Rate grids are bounded to 2001 rates and eCOCO
to 2001 windows; rate × window × (`nsim`+1) must be at most ten million.

## Preprocessing and scientific conditioning

Default `detrend: linear` uses the original per-record/slice/window linear detrending.
The original full-record helper removes nonfinite rows, sorts depths, averages
duplicates and conditionally interpolates to the median spacing. Interleaved eCOCO
retains raw observations for the original split-first preprocessing.

Optional `detrend: lowess` or `loess` requires exactly one `span` fraction or
`detrend_window`. The adapter extracts the calls `smooth(x,y,span,method)` and
`y-trend` from Acycle `code/guicode/detrending.m` (LOWESS/LOESS callbacks), then invokes
the original median-grid interpolation. A physical requested width is converted to
the fraction of total record depth range; this follows Acycle-style span entry, not
a new exact physical-distance kernel. MATLAB `loess` is quadratic; `lowess` is linear.
The original COCO code still performs its internal linear detrending afterward.

Global nonlinear preprocessing is disabled for Blocked/Interleaved eCOCO to avoid
mixing held-out information. Its Monte Carlo conditioning must also be explicit:
the upstream null is conditional on the transformed record, and does not re-fit
the global LOWESS/LOESS trend in each simulated realization. Large missing intervals
and choosing preprocessing or target settings after looking at results require
separate scientific consideration.

## Outputs and interpretation

Every run saves `analysis.mat`, `details.json`, source provenance, input coordinates
in metres, target periods and original MATLAB figures. COCO CSV columns include
rate, correlation, descriptive parametric p, missing orbit count, **rate-global**
Monte Carlo p, contributing orbit count, and same-rate local Monte Carlo p.
The parametric correlation p-value is never the formal significance result.
For `phase_averaged`, the public summary reports the actual requested and resolved
period counts, target construction and null conditioning. The original publication
report hardcodes nine-period/coherent wording; it is retained unchanged in the MAT
file for auditing, with its scope explicitly marked. The wrapper corrects only the
public interpretation text, leaving numerical statistics and original plots intact.

eCOCO writes a long-form map CSV plus the upstream tracked-rate table. Its global
p-values correct the sedimentation-rate search **within each window**, not the
search across windows. A chosen ridge and its local score range are descriptive;
the range is not a confidence interval. The minimum attainable Monte Carlo p-value
is `1/(nsim+1)`; a small quick-test budget is not sufficient evidence for a fine
significance threshold. The original COCO report supplies a precision qualification.

Published studies using earlier Acycle/COCO algorithms are validated at explicitly
stated levels. Running a paper's data through modern code is not automatically a
reproduction of its historical target construction, null model, chronology or
conclusion. See the benchmark manifest and recorded expected-versus-observed checks.

## Minimal examples

```json
{
  "input_path": "data/newark.txt",
  "parameters": {
    "depth_unit": "m", "middle_age_ma": 210,
    "sedimentation_rate_min": 8, "sedimentation_rate_max": 16,
    "sedimentation_rate_step": 1, "method": "adaptive",
    "nsim": 19, "seed": 1
  }
}
```

Use this argument object with `acycle_coco`. For a quick `acycle_ecoco` check on a
record at least 1500 m long, additionally specify `window: 500` and `step: 500`.
These small-budget examples test execution and provenance; increase simulations
and assess Monte Carlo precision before drawing scientific conclusions.

Required toolbox functionality is Signal Processing and Statistics and Machine
Learning. LOWESS/LOESS requires Curve Fitting. No Parallel Computing toolbox is
required: original serial/batched paths are used. Optimization is optional for
upstream robust-red-noise fitting (`red_noise: 2`), whose original implementation
can choose its grid-search alternative when `lsqcurvefit` is unavailable.

Attribution: Li, M., Hinnov, L.A., and Kump, L.R. (2019),
[Acycle](https://doi.org/10.1016/j.cageo.2019.02.011); Li, M. et al. (2018),
[Tracking variable sedimentation rates and astronomical forcing in Phanerozoic
paleoclimate proxy series with evolutionary correlation coefficients and hypothesis
testing](https://doi.org/10.1016/j.epsl.2018.08.041).
