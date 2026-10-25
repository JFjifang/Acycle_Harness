# Acycle for DeepSeek Harness

This native Cordis bundle registers Acycle tools and packaged research skills. Python
transports requests to MATLAB; Acycle original functions perform the scientific work.
A missing MATLAB backend is an error, never a request to substitute Python numerics.

1. Install the matching Python wheel with `python -m pip install acycle_deepseek-0.3.0-py3-none-any.whl`.
2. Set `ACYCLE_PYTHON` to that Python executable, `ACYCLE_ROOT` to an Acycle source checkout,
   and configure a local MATLAB executable or the documented GitHub backend.
3. Add the npm tarball using `dsh plugin --profile <profile> add /absolute/path/dsh-acycle-0.3.0.tgz`.
4. Restart the profile. `acycle_capabilities` reports backend readiness.

The bundle's `cordis.patch.yml` inserts `dsh-acycle`. Optional row config fields are
`python`, `workspace`, and `timeoutMs`. By default the workspace comes from Harness's
`workingDirectory` service for the calling agent, then the process directory for
non-agent calls. `ACYCLE_WORKSPACE` sets a fixed workspace. Paths and tool arguments
travel over stdin as JSON, never through a shell. The plugin propagates cancellation
to its local Python/MATLAB process group. A remote GitHub job's cancellation is
controlled by the backend implementation.

Harness configures its model provider separately. Keep `DEEPSEEK_API_KEY` in the
runtime environment only. The included Python live-test client defaults to the official
`deepseek-flash` model ID and records the model ID returned by the API.

Compatibility was checked against DeepSeek Harness master
`22ddee3792402c3e70ec5f86a63c3e3e895a2f60` (0.2.1-rc.3):
`ctx.tools.register(ToolDefinition)`, `ctx.skills.registerProvider`, and
`ctx.workingDirectory.ensure`. This package declares the corresponding DSH engine range.

The release tarball was also installed and checked with the published official
`@deepseek-ai/dsh-tools`, `dsh-system-prompt`, and `dsh-skill` 0.2.1-rc.3 packages
and Cordis 4.0.5. The smoke test checks tool execution, skill loading, and disposal;
it uses a fixed-directory fixture and does not represent a full desktop UI test.
The npm `latest` tag can lag these versions, so use explicit versions for verification.

The lightweight npm package contains tools and skills. Paper benchmark datasets and
their extraction scripts are in the full release bundle or the repository's
`benchmarks/` directory; obtain those separately when following a reproduction skill.
