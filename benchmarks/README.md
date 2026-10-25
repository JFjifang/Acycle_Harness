# MATLAB workflow and paper-data benchmarks

`manifest.json` pins six official Acycle example files and two public paper-derived fixtures. The original Acycle checkout is external; set `ACYCLE_ROOT` to commit `dcba4279168745b563e0535b954297023dd62fc7`. Input hashes are checked before execution. The benchmark runner calls the same public tool interface available to DeepSeek; scientific processing and figures execute in MATLAB.

```sh
python benchmarks/run.py --workspace . --case official-wayao
python benchmarks/run.py --workspace . --case paper-petm-ms --case paper-cambrian-gr
```

Use `ACYCLE_BACKEND=local` with MATLAB, or configure the GitHub backend described in the repository README. Without MATLAB or a working remote MATLAB workflow these cases fail; they do not fall back to Python calculations. `validation/benchmark-runs.json` records outcomes only after an actual run. The manifest itself makes no pass claim.

For numerical parity and image-output checks, use `matlab/run_validation.m`. Workflow execution, direct-function parity, model tool-use acceptance and full paper reproduction are separate claims.

## Paper sources and exact scope

**Li et al. (2022), “Astrochronology of the Paleocene-Eocene Thermal Maximum on the Atlantic Coastal Plain,” Nature Communications 13, 5618.** [Paper](https://doi.org/10.1038/s41467-022-33390-x). The authors provide calcium, magnetic susceptibility and isotope data, and identify Acycle among their tools. Our fixture selects the magnetic susceptibility observations from 194–200 m in sheet `Ca & MS`, columns D/E of Supplementary Data 1. Python copies these cells without a numerical transform. This 837-point slice is a realistic input/processing test. It does **not** reproduce the published Lomb–Scargle, COCO, ASM, tuning, PETM duration or cGENIE results; those require additional methods and the relevant full intervals.

**Zhao et al. (2022), “Synchronizing rock clocks in the late Cambrian,” Nature Communications 13, 1990.** [Paper](https://doi.org/10.1038/s41467-022-29651-4). The study uses Acycle 2.1 with detrending, MTM, robust AR(1), evoFFT and chronology analysis. Our 1655-point fixture is the complete numeric auxiliary gamma-ray record from `S4. Gamma-ray log_Albjära-1 core.xlsx`, sheet `GR_Albjära-1 core`, columns A/B. It exercises the supported MATLAB workflow on authentic paper data. It does **not** reproduce the paper's main Al-based astrochronology, eCOCO, 405-kyr node selection or duration estimates. The published analysis also predates the pinned Acycle version.

Both papers are open access under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), subject to credit lines for third-party material. Cite the papers when reusing their data. Extraction files are adaptations: source archives are unchanged, while CSVs contain selected columns/rows as documented. `sources/downloads.json` records publisher URLs, byte counts and original SHA-256 values; each CSV has a `.provenance.json` receipt containing exact source row numbers.

Recreate the CSVs with `python benchmarks/prepare_paper_data.py` (requires `openpyxl`). Add `--download` if the publisher originals are absent; downloads must match recorded checksums. No Python spectra or figures are generated.

## Acceptance and negative controls

For each executed case require a completed MATLAB response, recorded upstream provenance, processed data, spectral output and saved figures; inspect axes and coordinate units. Direct-function numerical checks belong to the MATLAB validation suite. A red-noise run is allowed to have pointwise exceedances; success means correct computation and qualified interpretation, not zero spectral peaks.

Sensitivity acceptance preserves an original run and creates independent branches (for example `span` 0.25/0.35/0.45). Record failures as well as successes. Do not select the strongest-looking branch and claim it as an independently confirmed orbital signal.
