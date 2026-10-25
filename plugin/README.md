# Acycle 0.5.1 for DeepSeek Harness

This native Cordis bundle registers Acycle tools and packaged research skills. Python
transports requests to MATLAB; Acycle original functions perform the scientific work.
A missing MATLAB backend is an error, never a request to substitute Python numerics.
The shared Python/MCP interface has twelve tools; this native package adds
`acycle_import_attachment` for thirteen Harness tools and ten skills.

1. Install the matching `acycle_deepseek-0.5.1-py3-none-any.whl` in a Python virtual environment.
2. In the current Harness **0.2.1-rc.3 Desktop**, add `dsh-acycle-0.5.1.tgz` through its plugin manager. The bundle supplies a selectable **Acycle MATLAB** agent preset.
3. From the full handoff, run `local/render_config.py --workspace . --acycle-root /path/to/acycle --matlab /path/to/matlab`. Quit Desktop and merge its generated `local/generated/desktop.preset.patch.yml` entries into `~/.dsh/profiles/desktop/cordis.patch.yml` (or your configured `DSH_HOME`), preserving other entries. Reopen Desktop and select the Acycle agent. The generated paths belong to this preset; they do not change other agents.
4. Alternatively use `local/deploy_harness.py --install` and `local/launch_harness.py` for the official project-local Web application. The standalone Web runtime needs Node.js >=24.9.0. Run `local/doctor.py --run-matlab` to verify the local MATLAB installation.

Use Desktop's own plugin manager or bundled CLI for its profile. The standalone npm CLI deliberately cannot manage Desktop's profile. The [local handoff](https://github.com/JFjifang/Acycle_Harness/blob/main/docs/LOCAL_HANDOFF.zh-CN.md) contains the complete setup and merge instructions.

The bundle's `cordis.patch.yml` registers the `acycle` agent preset. Its native plugin
accepts `python`, `workspace`, `acycleRoot`, `matlabExecutable`, `backend`, and
`timeoutMs`. Explicit MATLAB/Acycle paths and backend selection apply only to the
bridge subprocess; they work when Desktop is opened from its application icon.
If omitted, the corresponding process environment is used. The generated local
preset selects the local MATLAB backend.

By default the workspace comes from Harness's `workingDirectory` service for the
calling agent. `workspace` or `ACYCLE_WORKSPACE` selects a fixed workspace. Paths
and tool arguments travel over stdin as JSON, never through a shell. Cancellation
propagates to the local Python/MATLAB process group. Keep the virtual environment's
Python path; do not dereference its executable symlink to the base interpreter.

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

Harness configures its model provider separately. Desktop can use its existing
provider settings. The generated Web deployment references `DEEPSEEK_API_KEY` in
the launch environment; no credential value is written into package configuration.

This release targets the current official Harness **0.2.1-rc.3** interfaces:
`ctx.tools.register`, `ctx.skills.registerProvider`, `ctx.workingDirectory.ensure`
and `ctx.systemPrompt.section`. It has no older-Harness fallback. The npm `latest`
tag currently lags the newest official release, so the Web installer names rc.3
explicitly. Package tests and actual agent composition are checked separately from
Electron/macOS GUI behavior and scientific interpretation.

The lightweight npm package contains tools and ten general research skills. The
full handoff also provides datasets, local configuration tools and the optional
literature-guided Newark demo. Use `--newark-demo` when generating its preset to add
the eleventh, dataset-specific skill. Current evidence is documented in
[0.5.1 acceptance](https://github.com/JFjifang/Acycle_Harness/blob/main/validation/v0.5.1/ACCEPTANCE.md);
the completed MATLAB/Newark rehearsal and its limitations remain in the
[0.5.0 record](https://github.com/JFjifang/Acycle_Harness/blob/main/validation/v0.5/ACCEPTANCE.md).
