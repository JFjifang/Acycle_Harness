# Acycle 0.5 local handoff

Give `local/HANDOFF_PROMPT.txt` to a local Codex/DeepSeek Harness session after extracting the complete release. Detailed Chinese instructions: `docs/USER_GUIDE.zh-CN.md` and `docs/LOCAL_HANDOFF.zh-CN.md`.

The release has 12 shared Python/MCP tools, 13 native Harness tools and 10 skills. Six scientific operations use MATLAB: mini robot, SWA, COCO, eCOCO, Interpolation Pro and periodic-extrema tuning. No automatic Python numerical fallback is provided.

| Entry point | Scope |
| --- | --- |
| `install_check.py` | Installed 0.5.0 package, archive bytes and actual MCP; optional native registry. No API/MATLAB. |
| `doctor.py` | Paths/source hashes; `--run-matlab` starts MATLAB once and retains all diagnostic evidence. |
| `render_config.py` | Project-local Codex MCP and environment snippets; never overwrites host config. |
| `deploy_harness.py` | Pinned official Harness 0.2.1-rc.3 Web/native deployment, project-private runtime/home/profile/preset. |
| `check_harness.py` | Actual `acycle` preset agent, scoped persona/tools/skills, skill pre-step messages and image capability. Keyless fixture, no science. |
| `launch_harness.py` | Launch generated Web deployment with inherited credential and configured MATLAB environment. |
| `smoke.py` | Bounded real MATLAB requests; `--dry-run` only prints the plan. |

Use the matching virtual environment interpreter. The supported Harness route requires Node.js ≥24.9, the official Web app/frontend and the actual scoped `acycle` preset. Leave the old Desktop installation/configuration unchanged. The generated provider references `DEEPSEEK_API_KEY`; no credential value is saved. The default runtime, private `DSH_HOME`, npm cache and configuration live under `local/generated/harness-web/`.

`check_harness.py` goes beyond registry discovery: a real mounted AgentLoop with a deterministic adapter proves the official skill catalog is in actual request messages. It resolves the real deployment model catalog separately. This does not establish a successful real API call, scientific result, or user-visible browser image.

`smoke.py --case tune` performs a MATLAB depth/filter analysis, explicitly assumes 405 kyr with a relative zero at the first peak, then diagnoses the original proxy through `tuning_run_id`. Its 48–80 m illustrative band follows the public demo manifest, not independent cycle identification. `--case all` covers all six scientific operations and the dependent tuning chain. The default 19 simulations are diagnostic only.

MATLAB startup failures preserve `matlab-launch.json` and `matlab.log` in unique `.acycle/diagnostics/` or run directories. Do not automatically retry through a different shell or delete failed evidence. GUI delivery failures should reuse existing results, not rerun scientific calculations.

Current acceptance is in `validation/v0.5/ACCEPTANCE.md`. The official browser fixture `validation/v0.5/web/main-chat-final-fixture.json` verified two existing MATLAB PNGs in the main Chat, lightbox, refresh and original-byte file downloads with a text-only scripted provider. It is not a live-model test or a macOS Desktop test. Review live-model/image/scientific receipts separately. Historical 0.4 conversation failures and the unresolved SWA/PETM paper criteria remain part of the handoff; see the Chinese guide.

The live image lane retained two `read_image` image blocks and uploaded both through the official provider Files API. Its first browser runner timed out before lazy-loaded images were scrolled into view; that failed receipt is preserved. `validation/v0.5/web/main-chat-live-browser-replay.json` passed the same-session browser checks with zero new model requests, tool calls or scientific calculations. This is image transport/delivery evidence, not scientific interpretation acceptance.
