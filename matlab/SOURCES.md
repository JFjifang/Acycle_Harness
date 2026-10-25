# Acycle MATLAB adapter provenance

Reference: [mingsongli/acycle master](https://github.com/mingsongli/acycle/tree/dcba4279168745b563e0535b954297023dd62fc7), commit `dcba4279168745b563e0535b954297023dd62fc7`.

The installed Acycle checkout is the numerical implementation. This package does not redistribute or translate its numerical kernels into Python. `source_registry.json` pins SHA-256 hashes of reference files. Each run records actual source hashes, actual checkout commit when available, MATLAB release and toolboxes, and whether used sources match the reference. A changed hash is disclosed and does not automatically reject future Acycle versions; missing capabilities and incompatible outputs fail explicitly. This is a compatibility mechanism, not a promise that every future release is equivalent.

| Operation | Original source called | Adapter changes |
| --- | --- | --- |
| Remove non-finite, sort, merge duplicates | `code/guicode/RobotGUI.m`, preparation callback; `code/seriesanalysis/findduplicate.m` | Removes GUI dialogs; merge uses original function. |
| Interpolation | `code/seriesanalysis/acycleSamplingIsUneven.m`, `interpolate.m` | Same mean-spacing default and skip condition as mini robot; limits allocation. |
| Detrending | `code/guicode/RobotGUI.m`, detrend callback lines 489–502 | Extracted MATLAB `mean`, `polyfit`, `smooth` expressions; lowess span 0.35. Adds explicit `none`. No numerical rewrite. |
| Spectrum and original spectrum plot | `code/seriesanalysis/redconfML.m` and `rhoAR1.m`, `moveMedian.m`, `minirhos0.m`, `acycleMtmTaperCount.m` | Calls original with mini robot defaults NW=2, NFFT=5N, median fraction=0.25. Display FMAX is distinct from fit support. Uses original optimization or grid fallback. |
| Evolution | `code/seriesanalysis/zeropad2.m`, `evofft.m` | Original mini-robot zero padding, window 35%, normalized amplitude, adaptive step. Calls full Nyquist; requested FMAX affects displayed figure only. |
| Evolution plot | `code/guicode/RobotGUI.m`, lines 629–653 | Extracts `pcolor(y_grid,x_grid,s')`, `jet`, `shading interp`; removes GUI geometry and upper signal panel. |
| Gaussian / Taner-Hilbert filter and envelope | `code/seriesanalysis/acycleBandpassFilter.m` | Uses the current side-effect-free corrected core and its original metadata. New MATLAB plot, no copied or translated numerical algorithm. |
| Rate-age conversion | `code/seriesanalysis/acycleSedimentationRateAgeModel.m`, `depthtotime.m` | Explicit depth units and rate cm/kyr; starts at first_age_kyr. |
| Tie-point time conversion | `code/seriesanalysis/depthtotime.m` | Requires increasing tie points covering the record; disables implicit extrapolation. |
| Saving | MATLAB `writematrix`, `save`, `savefig`, `exportgraphics`, `jsonencode` | CSV, MAT, editable FIG, PNG and JSON, all emitted in MATLAB. |

Original author attributions remain in Acycle sources: Mingsong Li and contributors; EvoFFT credits Linda Hinnov and Florian Maurer (2002), Brian Zurek (2007), Mingsong Li (2013/2018); depthtotime credits Linda Hinnov (2006) and Mingsong Li (2014). Robust AR(1) follows Mann & Lees (1996); filter lineage is documented in the original function. Adapter callback extractions are distributed under the package GPL-3.0 license.

`processed.csv` columns are coordinate, detrended value, trend. Robust spectrum columns are frequency, power, robust background, pointwise 90/95/99/99.9% thresholds; classic spectrum columns are frequency, power, running median, conventional AR(1) background. Evolution CSV has frequency across the first row and coordinate down the first column, with a NaN corner. `analysis.mat` retains full precision arrays and metadata. `filtered.csv` has coordinate, filtered value, Hilbert envelope.

Significance is pointwise; it is not multiple-testing corrected and does not establish an orbital interpretation. Rate/age models are supplied assumptions, not inferred astronomical solutions. EvoFFT preserves upstream edge and grid conventions, including synthetic zeros at record boundaries. This first version does not expose wavelet, COCO/eCOCO, TimeOpt, or every GUI function.

Validation invokes the original functions separately to check numerical equality for cleanup/interpolation/detrending, MTM, evolution, filtering, and age conversion. It also runs four official fixtures and a red-noise negative control and inspects generated images. Those are workflow validations, not full published-paper reproductions. A passing validation receipt must come from a real MATLAB run.
