# Acycle for DeepSeek Harness

Version 0.5.0 adds Acycle Interpolation Pro, extrema-based astronomical tuning, original-proxy time diagnostics, persistent MATLAB launch diagnostics, and a pinned project-local Harness Web deployment. Start with the [Chinese user guide](docs/USER_GUIDE.zh-CN.md), [local deployment handoff](docs/LOCAL_HANDOFF.zh-CN.md), or give a local Codex/Harness assistant [HANDOFF_PROMPT.txt](local/HANDOFF_PROMPT.txt). The separate [Newark demonstration](demo/newark-0.5.0/README.zh-CN.md) includes explicitly documented scientific presets.

MATLAB-first cyclostratigraphy tools for the official [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness). Numerical processing, spectra, significance, filters, envelopes, age conversion, figures, CSV and MAT output execute in MATLAB, calling original [Acycle](https://github.com/mingsongli/acycle) functions. Python handles tool schemas, input snapshots, orchestration, provenance and model communication. There is no automatic Python numerical fallback.

## Install and run

Requires Python 3.10+, MATLAB with Signal Processing, Statistics and Machine Learning, and Curve Fitting toolboxes, and an Acycle source checkout. Validated upstream reference: `dcba4279168745b563e0535b954297023dd62fc7`.

```sh
python -m pip install .
export ACYCLE_ROOT=/absolute/path/to/acycle
export MATLAB_EXECUTABLE=matlab
acycle-deepseek --workspace . tools
acycle-deepseek --workspace . call acycle_analyze --arguments-json '{"input_path":"data.csv","parameters":{"span":0.35,"evolution":true}}'
```

Inputs are numeric two-column coordinate/proxy text files inside the workspace or `ACYCLE_ROOT`. Every run freezes input bytes, preserves parameters and source hashes, and writes to `.acycle/runs/<run_id>`. Sensitivity variants retain the baseline run ID. Results include MATLAB figures (`.png`, editable `.fig`), numeric CSVs, `analysis.mat`, and provenance.

For GitHub-hosted MATLAB, install `gh`, authenticate using your normal credential configuration, and set:

```sh
export ACYCLE_BACKEND=github
export ACYCLE_GITHUB_REPO=JFjifang/Acycle_Harness
export ACYCLE_GITHUB_REF=main
```

Each analysis dispatches the repository's MATLAB workflow and downloads its outputs. Input data is transmitted to that repository's Actions run; choose a private repository for private data. Initial uploads support files up to 1 MiB subject to GitHub's encoded workflow-input limit; registered outputs from the same repository can be reused by verified artifact reference without re-encoding their bytes. Use local MATLAB for larger inputs. The DeepSeek API key stays in the caller environment and is never sent to GitHub.

See [GitHub Actions execution and cloud transport](docs/GITHUB_ACTIONS.md) for credentials, limits and the optional connector transport required when a managed cloud blocks GitHub's artifact storage domain. Connector mode requires an external authorized agent; setting its cache variable alone does not download artifacts.

## Harness and model access

See [plugin/README.md](plugin/README.md) for the native Cordis plugin. MCP is available through `python -m acycle_deepseek.mcp`. Both interfaces use the same twelve Python tools and MATLAB adapter. The native Harness plugin additionally exposes `acycle_import_attachment`, making thirteen tools in Harness, with ten skills; MCP uses workspace file paths. Set `DEEPSEEK_API_KEY` only in the process environment. The official API model ID `deepseek-flash` identifies DeepSeek-V4.1-Flash. Use the local project deployment to verify the actual agent preset, model image route and skill catalog; a global plugin registry alone does not verify an active conversation.

Core methods: mini-robot preprocessing, MTM robust AR(1) pointwise thresholds, EvoFFT, Gaussian/Taner filtering and Hilbert envelopes, and sedimentation-rate/tie-point age conversion. `acycle_swa`, `acycle_coco`, and `acycle_ecoco` expose original SWA/FDR and explicit orbital-target/rate-grid Monte Carlo workflows. `acycle_interpolate_pro` preserves all nine GUI interpolation modes and explicit gap/grid policies. `acycle_tune` uses original peak/trough detection and depth–time conversion; `acycle_analyze(input_path=original_proxy, tuning_run_id=...)` applies saved controls to the original proxy within their covered interval. These tools support immutable runs, provenance and conversational steering. See [Interpolation/tuning sources](docs/INTERPOLATION_TUNING_SOURCES.md), [SWA](docs/SWA.md), [COCO/eCOCO](docs/COCO.md) and [paper validation protocols](docs/PAPER_VALIDATION.md) for scope and statistical meanings.

Future Acycle versions are loaded at runtime; required functions are checked and actual source hashes are recorded. See [matlab/SOURCES.md](matlab/SOURCES.md) and the SWA/COCO source registries for original-code provenance. Full-record nonlinear preprocessing is rejected for held-out eCOCO modes to prevent leakage between training and validation data.

## Validation and limitations

The historical v0.4 conversation suite uses the published official Harness SDK and `deepseek-flash`, uploads files through its attachment store, and sends independent user turns from [four predeclared scenarios](tests/fixtures/conversation_scenarios.json). Only the natural-language prompts and attachments reach the model; expected operations and acceptance rules stay outside its context. It tests Newark detrending changes, SWA display changes, eCOCO window changes, and clarification when scientific context is missing. See [current acceptance](validation/v0.5/ACCEPTANCE.md) for separate execution, delivery, steering and scientific-behavior results, including failures. Transport completion alone is not acceptance. Version 0.5 separately exercises the complete Newark workflow with its public demonstration skill and disclosed priors; this preset-assisted case is not a blind method-selection benchmark.

`scripts/harness_conversation.mjs --runtime /path/to/official-runtime --case CASE --workspace /new/study --output receipt.json` runs a case with the configured MATLAB backend. The [local handoff](docs/LOCAL_HANDOFF.zh-CN.md) explains runtime installation and the local MATLAB route. `--mode mock` checks infrastructure only; the older `live_*test.py` scripts test Python tool loops and do not establish a native Harness conversation.

```sh
python -m pytest -q
node --test plugin/tests/*.test.mjs
matlab -batch "addpath('matlab'); run_validation(getenv('ACYCLE_ROOT'),'validation/matlab')"
```

Tests compare the bridge against direct original-function calls, run official fixtures, inspect exported figures, and exercise negative controls and immutable steering. Validation evidence is recorded under `validation/`; paper-derived workflow checks must not be described as full paper reproduction. Pointwise spectral thresholds alone do not establish orbital forcing or control selection across frequencies and sensitivity variants.

This is a bounded initial integration, not the entire Acycle GUI. For unsupported methods, prefer a sourced MATLAB bridge; user-authorized Python extensions may handle features absent from Acycle and should return data to MATLAB whenever feasible.

License: GPL-3.0-or-later. Acycle remains separately installed and retains its authorship and license.
