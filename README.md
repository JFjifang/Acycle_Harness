# Acycle for DeepSeek Harness

Version 0.4.0 adds session-scoped attachment import, MATLAB figure delivery in Harness, and method-preserving conversational reruns. Start with the [Chinese user guide](docs/USER_GUIDE.zh-CN.md), [local deployment handoff](docs/LOCAL_HANDOFF.zh-CN.md), or give a local Codex/Harness assistant [HANDOFF_PROMPT.txt](local/HANDOFF_PROMPT.txt).

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

Each analysis dispatches the repository's MATLAB workflow and downloads its outputs. Input data is transmitted to that repository's Actions run; choose a private repository for private data. The transport supports files up to 1 MiB subject to GitHub's encoded workflow-input limit; use local MATLAB for larger inputs. The DeepSeek API key stays in the caller environment and is never sent to GitHub.

See [GitHub Actions execution and cloud transport](docs/GITHUB_ACTIONS.md) for credentials, limits and the optional connector transport required when a managed cloud blocks GitHub's artifact storage domain. Connector mode requires an external authorized agent; setting its cache variable alone does not download artifacts.

## Harness and model access

See [plugin/README.md](plugin/README.md) for the native Cordis plugin. MCP is available through `python -m acycle_deepseek.mcp`. Both interfaces use the same ten Python tools and MATLAB adapter. The native Harness plugin additionally exposes `acycle_import_attachment`, making eleven tools in Harness; MCP uses workspace file paths. Set `DEEPSEEK_API_KEY` only in the process environment and run `scripts/live_deepseek_test.py` or `scripts/live_extended_test.py` for a real model/tool test. The official API model ID `deepseek-flash` identifies DeepSeek-V4.1-Flash.

Core methods: mini-robot preprocessing, MTM robust AR(1) pointwise thresholds, EvoFFT, Gaussian/Taner filtering and Hilbert envelopes, and sedimentation-rate/tie-point age conversion. New tools `acycle_swa`, `acycle_coco`, and `acycle_ecoco` expose original SWA/FDR and explicit orbital-target/rate-grid Monte Carlo workflows. All three support the same immutable runs, provenance and steering interfaces. See [SWA](docs/SWA.md), [COCO/eCOCO](docs/COCO.md) and [paper validation protocols](docs/PAPER_VALIDATION.md) for their distinct statistical meanings and supported modes.

Future Acycle versions are loaded at runtime; required functions are checked and actual source hashes are recorded. See [matlab/SOURCES.md](matlab/SOURCES.md) and the SWA/COCO source registries for original-code provenance. Full-record nonlinear preprocessing is rejected for held-out eCOCO modes to prevent leakage between training and validation data.

## Validation and limitations

```sh
python -m pytest -q
node --test plugin/tests/*.test.mjs
matlab -batch "addpath('matlab'); run_validation(getenv('ACYCLE_ROOT'),'validation/matlab')"
```

Tests compare the bridge against direct original-function calls, run official fixtures, inspect exported figures, and exercise negative controls and immutable steering. Validation evidence is recorded under `validation/`; paper-derived workflow checks must not be described as full paper reproduction. Pointwise spectral thresholds alone do not establish orbital forcing or control selection across frequencies and sensitivity variants.

This is a bounded initial integration, not the entire Acycle GUI. For unsupported methods, prefer a sourced MATLAB bridge; user-authorized Python extensions may handle features absent from Acycle and should return data to MATLAB whenever feasible.

License: GPL-3.0-or-later. Acycle remains separately installed and retains its authorship and license.
