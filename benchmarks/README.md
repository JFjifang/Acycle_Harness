# MATLAB workflow and paper-data benchmarks

`manifest.json` pins six official Acycle example cases, two existing paper-data mini-robot cases, and three SWA/COCO/eCOCO paper cases. The original Acycle checkout is external; set `ACYCLE_ROOT` to commit `dcba4279168745b563e0535b954297023dd62fc7`. Input hashes are checked before execution. The runner calls each case's public tool (`acycle_analyze` by default); scientific processing and figures execute in MATLAB.

```sh
python benchmarks/run.py --workspace . --case official-wayao
python benchmarks/run.py --workspace . --case paper-petm-ms --case paper-cambrian-gr
python benchmarks/run.py --workspace . --case official-newark
python benchmarks/run.py --workspace . --case paper-weedon-swa --case paper-petm-coco --case paper-cambrian-ecoco
```

Use `ACYCLE_BACKEND=local` with MATLAB, or configure the GitHub backend described in the repository README. Without MATLAB or a working remote MATLAB workflow these cases fail; they do not fall back to Python calculations. `validation/benchmark-runs.json` records outcomes only after an actual run. The manifest itself makes no pass claim.

For numerical parity and image-output checks, use `matlab/run_validation.m`. Workflow execution, direct-function parity, model tool-use acceptance and full paper reproduction are separate claims.

The new paper cases and their exact scope are documented in [PAPER_VALIDATION.md](../docs/PAPER_VALIDATION.md). SWA requires the published approximately 0.81 m Lavernock peak above 5% FDR. The PETM COCO case uses the full below-unconformity MS interval, six published target periods, 20 m LOESS and 2000 Monte Carlo draws; it compares the modern implementation's best rate with the published broad 8–15 cm/kyr interval. The Cambrian eCOCO case uses primary Al, not auxiliary gamma ray, but deliberately reduces the published simulation/window budget and records the preprocessing differences. An execution that completes but misses a declared summary check is recorded as `acceptance_failed`; the underlying MATLAB run and its numerical results remain available. The runner does not compute spectra or fit models in Python.

The first expanded MATLAB CI run found the Lavernock peak at approximately 0.82125 m and passed direct-source numerical parity, but the original SWA implementation returned unavailable (`NaN`) FDR thresholds. The published 5% FDR feature is therefore **not reproduced**. Its original manifest check remains unchanged; rerunning that strict paper case can return a nonzero exit status while still producing valid original MATLAB artifacts. See the investigation and evidence links in the paper-validation document.

## Paper sources and exact scope

**Li et al. (2022), “Astrochronology of the Paleocene-Eocene Thermal Maximum on the Atlantic Coastal Plain,” Nature Communications 13, 5618.** [Paper](https://doi.org/10.1038/s41467-022-33390-x). `paper-petm-ms` retains the original 837-point, 194–200 m mini-robot smoke case. `paper-petm-coco` uses a separate 5027-point fixture covering the MS below the Nanjemoy unconformity. Both select sheet `Ca & MS`, columns D/E, without numerical transformation. The modern COCO comparison does not reproduce the full chronology, ASM, TimeOpt or cGENIE analysis.

**Zhao et al. (2022), “Synchronizing rock clocks in the late Cambrian,” Nature Communications 13, 1990.** [Paper](https://doi.org/10.1038/s41467-022-29651-4). `paper-cambrian-gr` retains the complete 1655-point auxiliary gamma-ray smoke case. `paper-cambrian-ecoco` selects 18001 raw Al observations at 0–18 m from S2, columns A/C. Author-corrected depth is retained, while the tuned age column is excluded. This is a reduced modern eCOCO workflow, with explicit differences from the published full-record Acycle 2.1 analysis.

**Weedon (2020), “Confirmed detection of Palaeogene and Jurassic orbitally-forced sedimentary cycles in the depth domain using False Discovery Rates and Bayesian probability spectra,” Boletín Geológico y Minero 131, 207–230.** [Paper](https://doi.org/10.21701/bolgeomin.131.2.001). `paper-weedon-swa` selects the untuned Lavernock MS interval discussed at Fig. 11, from [PANGAEA.896872](https://doi.org/10.1594/PANGAEA.896872), originally deposited with Weedon, Page & Jenkyns (2019), [DOI](https://doi.org/10.1017/S0016756818000808). SWA means Smoothed Window Averages. Actual observations span 0.03–13.17 m, with 439 rows; Python preserves the original descending row order, and MATLAB handles sorting. No Bayesian inference is reproduced.

The two Nature Communications papers and the PANGAEA dataset are available under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), subject to credit lines for third-party material. Cite the papers and dataset when reusing data. Extraction files are adaptations: source archives are unchanged, while CSVs contain selected columns/rows as documented. `sources/downloads.json` records publisher URLs, byte counts and original SHA-256 values; each CSV has a `.provenance.json` receipt containing exact source row numbers.

Recreate the CSVs with `python benchmarks/prepare_paper_data.py` (requires `openpyxl`). Add `--download` if the publisher originals are absent; downloads must match recorded checksums. No Python spectra or figures are generated.

## Acceptance and negative controls

For each executed case require a completed MATLAB response, recorded upstream provenance, processed data, spectral output and saved figures; inspect axes and coordinate units. Direct-function numerical checks belong to the MATLAB validation suite. A red-noise run is allowed to have pointwise exceedances; success means correct computation and qualified interpretation, not zero spectral peaks.

Sensitivity acceptance preserves an original run and creates independent branches (for example `span` 0.25/0.35/0.45). Record failures as well as successes. Do not select the strongest-looking branch and claim it as an independently confirmed orbital signal.
