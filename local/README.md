# Acycle 0.5.1 local handoff

Give [HANDOFF_PROMPT.txt](HANDOFF_PROMPT.txt) to a local Codex/DeepSeek Harness session after extracting the release. The [Chinese local handoff](../docs/LOCAL_HANDOFF.zh-CN.md) provides a short install → MATLAB doctor → Desktop plugin route; the [user guide](../docs/USER_GUIDE.zh-CN.md) describes all methods.

This release targets official Harness **0.2.1-rc.3**, the newest verified release. Use the updated Desktop application and its bundled runtime; a separate system Node installation is unnecessary. A project Web deployment is also available, requiring Node.js **≥24.9.0** and the exact rc.3 package because npm’s `latest` tag currently points to rc.2.

There are 12 shared Python/MCP tools, 13 native Harness tools and 10 general skills. Six scientific operations use MATLAB: mini robot, SWA, COCO, eCOCO, Interpolation Pro and periodic-extrema tuning. Python provides orchestration and file transport.

| Entry point | Purpose |
| --- | --- |
| `install_check.py` | Installed 0.5.1 package, archive hashes and actual MCP; optional native registry. No API/MATLAB. |
| `doctor.py --run-matlab` | Check local MATLAB, license, toolboxes and original sources; retain diagnostics. |
| `deploy_harness.py --install` | Install the supported runtime and current plugin; generate the actual Acycle agent configuration. |
| `check_harness.py --output ...` | Verify the mounted agent's tools, skills and text/image capability without an API key. |
| `launch_harness.py` | Launch the generated Web deployment with local MATLAB paths and inherited credentials. |
| `render_config.py` | Generate the Desktop Acycle preset patch with local Python/MATLAB paths, plus Codex MCP configuration. |
| `smoke.py --case ...` | Optional method-specific MATLAB diagnostic; `--dry-run` prints requests. |

For Desktop, install `dist/dsh-acycle-0.5.1.tgz` through **Plugins → Add plugin**, then enable it. Run `render_config.py`, quit Desktop and merge `local/generated/desktop.preset.patch.yml` into `~/.dsh/profiles/desktop/cordis.patch.yml` (or the configured `DSH_HOME`) while preserving other entries. Reopen Desktop and select **Acycle MATLAB**. The patch configures the Acycle child process; existing Desktop model credentials remain in host settings.

Add `--newark-demo` to `render_config.py` to mount the public literature-guided Newark skill: 13 tools and 11 skills. See [the demo handoff](../demo/newark-0.5.1/HANDOFF.zh-CN.md) for its input and short prompts. Ordinary research sessions do not receive Newark-specific priors.

For the optional Web route, `deploy_harness.py --install [--newark-demo]` installs the runtime under `local/generated/harness-web/`; `--runtime` reuses an existing same-version installation. `launch_harness.py` reads credentials from `DEEPSEEK_API_KEY` in its process environment.

Check actual conversation results and images after launch. A saved `display_markdown` image should load in main Chat, open in a lightbox and remain visible after refresh; original files should download intact. If display fails, reuse the completed run rather than recalculate it. Preserve MATLAB failure logs and diagnose the cause before retrying.

Current release checks: [0.5.1 acceptance](../validation/v0.5.1/ACCEPTANCE.md). Historical full Newark conversation, image and science evidence: [0.5 acceptance](../validation/v0.5/ACCEPTANCE.md). Shared runtime/configuration tests do not establish an Electron GUI test on the user’s machine; local testing and scientific review remain separate.
