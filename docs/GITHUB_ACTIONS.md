# MATLAB on GitHub Actions

`matlab.yml` runs the same MATLAB adapter as a local MATLAB installation. It
checks out the pinned Acycle revision, installs MATLAB R2024b and the Signal
Processing, Statistics and Machine Learning, and Curve Fitting toolboxes, then
runs numerical parity, official example and paper workflow tests. The runner is
pinned to Ubuntu 24.04. A push to `main`, a pull request or an empty manual dispatch
runs validation. Source revisions and actual MATLAB provenance are retained.
The full validation artifact includes MATLAB data and editable figures; a
separate `acycle-validation-report` artifact contains JSON/JUnit receipts and
PNG previews for hosts with smaller file-download limits.

The remote backend uses a manual dispatch for each analysis:

```sh
export ACYCLE_BACKEND=github
export ACYCLE_GITHUB_REPO=owner/repository
export ACYCLE_GITHUB_REF=main
# Configure the ordinary gh CLI with an authorized runtime GH_TOKEN.
acycle-deepseek --workspace . call acycle_analyze --arguments-json '{"input_path":"benchmarks/data/petm_2022_ms_194_200m.csv","parameters":{"evolution":true,"coordinate_unit":"m"}}'
```

The workflow must already exist on the repository's default branch; the selected
ref must contain the adapter and workflow. GitHub authentication needs permission
to dispatch workflows and read runs/artifacts. No DeepSeek API key is sent to
GitHub. Input datasets, parameters and scientific outputs are sent to the selected
repository's Actions service; choose the repository's visibility accordingly.

Input transport accepts CSV/TXT/DAT/TSV files up to 1 MiB, subject to the tighter
60,000-character encoded workflow-input limit after gzip compression. Larger
inputs should run with local MATLAB. Every remote request has a unique token;
results are matched to that exact token and include the run URL, source commit,
upstream revision, artifact SHA-256 and transport used. MATLAB writes the data,
figures and numerical results. Python transports files and records provenance.

## Standard artifact retrieval

By default the backend uses `gh api` to download the ZIP artifact, checks the
SHA-256 supplied by GitHub when available, rejects unsafe ZIP entries, and maps
MATLAB's output paths into the local run directory. It never substitutes Python
calculations if MATLAB or artifact retrieval fails.

## Managed cloud connector transport

Some managed cloud environments permit GitHub's API but block the signed Azure
Blob destination used for Actions artifact downloads. The observed test-session
failure was a proxy `403` at the storage connection, even after removing all
Authorization headers from the redirected request. The GitHub connector's
supported artifact-download tool remained available.

In such an environment, enable the explicit connector cache transport:

```sh
export ACYCLE_ARTIFACT_CACHE=/workspace/acycle-artifacts
export ACYCLE_ARTIFACT_CACHE_TIMEOUT=600
```

This mode **requires an external authorized host service or agent** to fulfill
artifact requests. The command-line package cannot independently call the
ChatGPT GitHub connector. Setting the cache variable alone does not provide
unattended artifact retrieval.

1. The backend waits for the MATLAB workflow to complete and writes
   `pending/<request-token>.json` under the cache. It contains only the repository,
   artifact ID, run ID/URL, token and destination path.
2. The authorized host invokes `github_download_workflow_artifact` for that exact
   repository and artifact ID, then downloads the returned platform file using
   the supported file-download tool.
3. The host copies the ZIP to a temporary file on the cache filesystem and
   atomically renames it to `<artifact-id>.zip` at the requested destination.
4. The backend checks its SHA-256 against GitHub's receipt, validates/extracts the
   ZIP, verifies the request token, and resumes the model's tool call.

The result explicitly records `artifact_transport: github_connector_cache`.
Direct mode records `artifact_transport: gh`. This option does not alter proxy
configuration, send credentials to an alternate storage host, or replace any
scientific computation. A timeout reports the pending request and the already
completed MATLAB run; fulfill the transfer instead of repeating the analysis.
Do not save signed artifact URLs or provider API keys in logs or receipts.
