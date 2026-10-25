# Acycle 0.5 for DeepSeek Harness

This native Cordis bundle registers Acycle tools and packaged research skills. Python
transports requests to MATLAB; Acycle original functions perform the scientific work.
A missing MATLAB backend is an error, never a request to substitute Python numerics.
The shared Python/MCP interface has twelve tools; this native package adds
`acycle_import_attachment` for thirteen Harness tools and ten skills.

1. Install the matching Python wheel with `python -m pip install acycle_deepseek-0.5.0-py3-none-any.whl`.
2. Set `ACYCLE_PYTHON` to that Python executable, `ACYCLE_ROOT` to an Acycle source checkout,
   and configure a local MATLAB executable or the documented GitHub backend.
3. Add the npm tarball using `dsh plugin --profile <profile> add /absolute/path/dsh-acycle-0.5.0.tgz`.
4. Ensure the actual agent preset contains this plugin, its skills and persona. Prefer the project-local `local/deploy_harness.py` / `local/launch_harness.py` Web deployment, pinned to 0.2.1-rc.3. The older 0.1.2 Desktop MCP path has different rendering and agent-scope behavior. Restart the profile. `acycle_capabilities` reports configuration; an actual scientific call verifies MATLAB execution.

The bundle's `cordis.patch.yml` inserts `dsh-acycle`. Optional row config fields are
`python`, `workspace`, and `timeoutMs`. By default the workspace comes from Harness's
`workingDirectory` service for the calling agent, then the process directory for
non-agent calls. `ACYCLE_WORKSPACE` sets a fixed workspace. Paths and tool arguments
travel over stdin as JSON, never through a shell. The plugin propagates cancellation
to its local Python/MATLAB process group. A remote GitHub job's cancellation is
controlled by the backend implementation. Keep the virtual environment's Python path;
do not dereference its executable symlink to the base interpreter.

## Attach a dataset and continue the conversation

Upload a two-column CSV, TXT, DAT, or TSV in the current Harness session. A short first
message can state the coordinate unit, proxy, and question, for example:
“This is depth in metres and magnetic susceptibility. Show its period structure,
without assigning orbital periods yet.” After the result arrives, send a separate
message such as “Keep that baseline and double the detrending window, then compare.”
The model should establish missing scientific metadata before computing results
that depend on it; users need not supply tool names or JSON.

`acycle_import_attachment` accepts an optional `attachment_id`. Without it, the tool
selects the single file in the latest user message containing files. Multiple files
return `selection_required` and choices instead of guessing. An explicit ID must
refer to a file in a user-origin message of this same session. The import preserves
bytes at `<workspace>/.acycle/imports/<sha256>/<filename>` and records the source
reference, session/message identity and hash. It never modifies the uploaded object.
An ordinary `input_path` matching that authorized attachment's official host path or
an unambiguous filename can also be imported automatically.

The official eight-character hexadecimal handle is accepted only when it uniquely
identifies a full attachment ID in this session; ambiguous prefixes return choices.
A bare filename first selects the session's unique matching upload, before an old
workspace file; ambiguous uploads require selection. Use `./name` or an absolute
workspace path to explicitly select a workspace file. Repeated imports reuse the
verified bytes but create a new `.source-<uuid>.json` receipt beside them, preserving
the current session/message provenance without replacing earlier receipts.

Attachment import uses the official attachment and session-query services. When
they are unavailable, workspace-path analysis remains available and import reports
the missing dependency. An ID from another session or an arbitrary filesystem path
does not grant attachment access. Codex MCP uses the twelve shared tools and workspace
paths; this Harness-specific import tool is not part of MCP.

`acycle_rerun({run_id, parameter_patch, label?})` applies a conversational change to
the saved scientific operation and frozen input, retains other effective settings,
and creates an immutable child run. An SWA/COCO/eCOCO adjustment stays in that
operation; its method changes only through an explicit `method` patch. Use
`acycle_sensitivity` for several values of one parameter, then `acycle_compare` to
read the saved results. A default derived from a changed setting may be recomputed
in MATLAB; an explicit user choice remains fixed. The branch records every removed
or reset setting in `steering.removed_or_reset_parameters`. These operations do not
overwrite the baseline.

## Return MATLAB figures and files

The plugin returns official image and file references plus Markdown links. Image
previews are marked `offloaded: true`, so this automatic delivery does not send their
pixels to the model. A host-provided `read_image` tool and an image-capable provider
may separately let the model inspect a figure; verify that actual tool/provider path
before claiming visual inspection. The supported project-local Web deployment is tested separately for main-chat PNG rendering, lightbox enlargement, refresh persistence and byte-identical downloads; consult the version-specific receipt before assuming another client behaves identically.
Original file attachments preserve
the MATLAB-generated bytes. When the official `present` tool and a calling agent
are available, the plugin invokes it for up to four key deliverables; otherwise the
delivery reports `links_only`. Check actual client display and downloads separately
from successful scientific execution or emitted attachment events.

Additional plugin configuration fields are `maxImportBytes` (32 MiB),
`maxArtifactBytes` (64 MiB), `maxPreviewImages` (4), `maxFileAttachments` (24),
`maxDeliveryRuns` (3), and `presentOutputs` (`true`). These bound transfer and
presentation; they do not change MATLAB's scientific parameters.

An oversized input is rejected before import. An oversized output is skipped for
attachment delivery while its original file and completed scientific run remain
available. Inspect `presentation.status` (`available`, `partial`, `paths_only`),
`presentation.delivery.status` (`presented`, `failed`, `links_only`,
`not_requested`), and `presentation.skipped` for paths and reasons. Presentation
errors do not require rerunning MATLAB; reopen the existing run and repair delivery.
`presentation.images`/`files` retain official references, source paths and hashes;
`display_markdown` and `warnings` support the user-facing explanation.

Harness configures its model provider separately. Keep `DEEPSEEK_API_KEY` in the
runtime environment only. The included Python live-test client defaults to the official
`deepseek-flash` model ID and records the model ID returned by the API.

Compatibility was checked against DeepSeek Harness master
`22ddee3792402c3e70ec5f86a63c3e3e895a2f60` (0.2.1-rc.3):
`ctx.tools.register(ToolDefinition)`, `ctx.skills.registerProvider`, and
`ctx.workingDirectory.ensure`. The attachment workflow additionally uses official
attachment/session-query services and optional `present`. This package declares the
corresponding DSH engine range.

The 0.3 release tarball was installed and checked with the published official
`@deepseek-ai/dsh-tools`, `dsh-system-prompt`, and `dsh-skill` 0.2.1-rc.3 packages
and Cordis 4.0.5. The smoke test checks tool execution, skill loading, and disposal;
it uses a fixed-directory fixture and does not represent a full desktop UI test.
Real 0.4 Harness conversations now verify autonomous analysis, separate user-turn
changes and official file/image delivery, but do not pass every scientific-behavior
or complete-task criterion. Newark completed both analysis turns with interpretation
caveats. SWA preserved its method and full-spectrum bytes but the model additionally
used NumPy numerical QA, violating the MATLAB-only boundary. PETM's adjusted window
failed in original MATLAB and produced no second map; the model retained the failure.
The missing-metadata case asked for necessary facts but had wording/interface errors.
See the full bundle's `validation/v0.4/conversation-evaluation.md` and interpretation
review. The final attachment edge-case fixes have official-service tests but were
not followed by another real API/MATLAB run. Web/Desktop rendering was not tested.
The npm `latest` tag can lag these versions, so use explicit versions for verification.

The lightweight npm package contains tools and skills. Paper benchmark datasets and
their extraction scripts are in the full release bundle or the repository's
`benchmarks/` directory; obtain those separately when following a reproduction skill.

Version 0.5 adds Interpolation Pro and extrema-based tuning to the same interfaces. Its local MATLAB supervisor launches once, distinguishes startup failure from computation timeout, and retains logs plus a launch receipt in the run output directory. Structured tool failures retain the run ID and diagnostic locations. See `validation/v0.5/ACCEPTANCE.md` for the separate engineering, model, Web-rendering and scientific checks; the historical 0.4 limitations above remain historical evidence.
