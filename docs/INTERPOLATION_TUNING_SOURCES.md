# Interpolation Pro and periodic-extrema tuning: MATLAB sources

These operations use the separately installed Acycle checkout. The source reference
is [Acycle `dcba4279168745b563e0535b954297023dd62fc7`](https://github.com/mingsongli/acycle/tree/dcba4279168745b563e0535b954297023dd62fc7).
`matlab/preparation_sources.json` records exact file hashes. Each result records
actual source and adapter hashes, MATLAB release/toolboxes and the input hash.
A changed source is reported; it does not make an extracted callback automatically
compatible with a future GUI implementation. Required original functions must exist
and must not be shadowed. No Python numerical or plotting replacement is used.

| Operation | Original source | Reuse and declared adaptation |
| --- | --- | --- |
| Interpolation Pro methods | `code/guicode/interpolationGUI.m:34` | All nine actual GUI methods: linear, nearest, next, previous, pchip, cubic, v5cubic, makima, spline. |
| Pro default interval | `interpolationGUI.m:103–108` | Median input spacing, passed through the original edit box's 10-significant-digit representation. |
| Pro interpolation | `interpolationGUI.m:152–218` | Extracted MATLAB colon grid, original two-endpoint fallback, `interp1` method call, and optional strict-interior gap zeroing. |
| Tuning preparation/peaks | `code/guicode/AC.m:4613–4624`; `code/seriesanalysis/findduplicate.m`, `getpks.m` | Finite two-column data, sorting, original duplicate averaging; direct original peak function, or the same function on the negated values for troughs. |
| Single-kind cycle assignment | `AC.m:4629–4633` | Original GUI assigns `(1:n)*period`. The bridge exposes an explicit anchor and records the resulting offset. |
| Apply age model | `code/guicode/agescale.m:351–352`; `code/seriesanalysis/depthtotime.m` | Direct original piecewise-linear depth-to-time conversion, preserving signal values. |

Tuning preparation makes one explicit ordering adaptation: all nonfinite rows are
removed before original duplicate averaging. The GUI removes Inf after that step;
with an infinite and a finite observation at the same depth, its mean can discard
the finite measurement too. The bridge's finite-first policy retains it and records
the changed cleanup contract. The peak detector and time-conversion functions are
called directly without alteration.

Original attribution: Mingsong Li and Acycle contributors; `depthtotime` credits
Linda A. Hinnov (2006) and Mingsong Li (2014). Cite Li, Hinnov & Kump (2019),
[Acycle](https://doi.org/10.1016/j.cageo.2019.02.011). GUI callback extractions retain
their source attribution and are distributed under this package's GPL license.

## Interpolation Pro contract

`operation: interpolate_pro` takes an exactly two-column numeric file. It sorts
coordinates as the original GUI does. Unlike mini-robot preprocessing, it does not
silently remove nonfinite values or average duplicate positions: those inputs are
rejected for explicit preparation. At least two finite unique coordinates are needed.

Parameters are `method` (default `linear`), optional positive `dt`, `coordinate_unit`
(a label), `gap_policy` (`interpolate` default or `zero`), positive `gap_multiplier`
(default 10), and `endpoint_policy` (`gui` default or `strict_grid`). The selected
MATLAB method's own sampling requirements and errors remain in force. There is no
FFT interpolation option in the current GUI, even though an old comment mentions
one. This operation does not call the different, linear-only
`acycleInterpolateSeries` core and is not ordinary interpolation renamed "Pro".

The grid is the original `first:dt:last`. A trailing input endpoint that is off
that grid is not appended. Nothing is extrapolated. With `endpoint_policy: gui`,
if the requested interval produces fewer than two points, the original GUI fallback
uses `linspace(first,last,2)`; the receipt distinguishes requested dt from actual
spacing. `strict_grid` is a documented bridge safeguard that rejects this fallback
instead of changing the requested interval. Output is limited to 200000 points.

With `gap_policy: zero`, the exact original rule is `input_spacing > dt *
gap_multiplier`, and only query points strictly inside those gaps become zero.
The GUI's historical label says "median sampling rate", but its implementation
uses the **requested dt**. Observed gap endpoints retain their interpolated values.
The default interpolates across gaps using the selected method. Neither setting
adds an anti-alias filter, and zero-filled gaps are synthetic values that can affect
subsequent spectra. Resampling does not create independent observations.

MATLAB emits raw/cleaned/interpolated two-column CSVs, a gap-boundary CSV, a
diagnostic PNG/PDF/editable FIG, `analysis.mat` and source provenance. The summary
contains actual spacing, retained range, unfilled tail, gap threshold/count,
zero-filled row count and whether the GUI endpoint fallback occurred. An empty gap
CSV simply denotes no selected gaps. The MAT retains full arrays, including the
mask identifying synthetic gap zeros.

## Periodic tuning contract

`operation: tune` expects a **user-declared bandpassed curve**, not an unfiltered
proxy. It accepts depth/value or the existing filter output's depth/value/envelope
columns; only the first two participate. The third envelope column is explicitly
recorded as ignored. The tool cannot independently verify that the chosen frequency
band represents an astronomical component.

Required assumptions are positive `period_kyr`, finite `anchor_age_kyr`,
`anchor_phase: peak|trough`, `extrema: peaks|troughs|both`, and
`depth_unit: m|dm|cm|mm|ft|km`. `endpoint_policy` defaults to `trim` and also permits
explicit `linear_extrapolate` or `error`.

The anchor age belongs to the **first selected extremum matching anchor_phase**.
For peak-only or trough-only tuning, the anchor phase must match that choice and
successive controls differ by a whole period. For `both`, original peaks and troughs
are merged by depth and must strictly alternate; adjacent controls differ by half
a period. If a selected trough precedes the first peak anchor, for example, its age
is `anchor_age_kyr - period_kyr/2`. The summary gives the exact anchor index/depth,
and the control table records cycle number relative to it. Ages increase with depth;
this is not a bidirectional absolute-age convention. Both-extrema half-cycle mapping
and explicit anchoring are bridge extensions to the original single-kind GUI.

The original `getpks` selects internal sampled points satisfying `>=` both neighbors.
It does not estimate sub-sample extrema or provide prominence, minimum-distance,
significance, or missed-cycle detection. Plateaus can therefore produce ambiguous
candidates. The bridge rejects any selected flat peak/trough and ambiguous merged
sequence, rather than substituting `findpeaks` or silently consolidating candidates.
At least two distinct selected controls are required. Missing or spurious extrema
can still miscount cycles; inspect the saved diagnostic plot. Input is limited to
300000 rows and the original depth-to-time nested-loop workload is capped at twenty
million sample-by-control intervals; oversized requests fail before conversion.

Endpoint policies:

- `trim`: retain only original samples from the first to last observed control.
  The exported model covers that range. Any other proxy subsequently converted with
  it must be restricted to `summary.valid_depth_range` in MATLAB.
- `linear_extrapolate`: explicitly assume that the nearest control-interval rate
  continues to each input edge. Original `depthtotime` computes those ages, and the
  exported age model includes the resulting endpoints. The observed control table
  remains separate; synthetic endpoint count and extrapolated sample count are saved.
- `error`: reject if the observed controls do not cover the input. Original peak
  detection excludes endpoints, so ordinary whole curves generally require one of
  the two explicit coverage treatments above.

The plot-only `agemodelfull` in `AC.m:4649,4651` multiplies a depth difference by a
depth/time rate, which is dimensionally inconsistent. That array is not the GUI's
exported control-point table. The bridge deliberately does not copy it: endpoint
conversion uses the original `depthtotime` division and is tested against that
function. This deviation is recorded in provenance.

Outputs are `control_points.csv` (depth, bandpass value, type +1 peak/−1 trough,
relative cycle, age_kyr), `age_model.csv` (depth, age_kyr), `depth_age.csv`,
`tuned.csv` (time, the supplied bandpass value), and `sedimentation_rate.csv`
(left depth, right depth, rate in cm/kyr). Rate conversion from the original
depth-unit/kyr result occurs in MATLAB. The three-panel diagnostic shows the input
curve and selected extrema, applied age model and explicit anchor, and implied
interval rates. MATLAB saves PNG/PDF/editable FIG, MAT and provenance.

The summary includes the exact applied `age_model`, `valid_depth_range`,
`recommended_depth_range` and `depth_unit`, so another operation can use those
controls without having Python interpolate or crop data. `analysis.mat` preserves
the original input, cleaned curve, observed controls, applied model and full arrays.
The tuned curve is not automatically resampled to a uniform time axis.

**Period assignment is an assumption, not an independent astronomical detection.**
Finding the assigned period in the tuned bandpassed curve is partly imposed by the
construction. A useful subsequent diagnostic converts the *original proxy* with the
same model, performs its declared time-domain analysis in MATLAB, and reports the
shared assumptions. This pipeline does not independently validate the chronology,
provide age uncertainties or reconstruct missed cycles.

## Validation scope

`test_acycle_interpolate_pro.m` compares all nine output methods against the actual
GUI's MATLAB expressions, tests exact gap threshold/interior behavior, grid tails,
default precision, the GUI endpoint fallback, explicit strict rejection and immutable
outputs. These are direct comparisons with a documented callback extraction; there
is no separately callable upstream Pro function to pretend to test.

`test_acycle_tune.m` independently calls original `getpks`, `findduplicate` and
`depthtotime`, including the original GUI's single-kind age assignment, both-extrema
phase mapping, trim/extrapolation, unit conversion, three-column filter input,
plateau rejection and immutable output. It checks saved plots and data. Actual
pass/fail belongs to the MATLAB validation receipt; source inspection alone is not
execution or an autonomous-model conversation test.
