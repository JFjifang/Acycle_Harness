# Local deployment helpers

Read `../docs/USER_GUIDE.zh-CN.md` for installation and `../docs/LOCAL_HANDOFF.zh-CN.md` for a self-contained handoff prompt.

- `render_config.py` writes reviewed configuration snippets only. It never edits Codex or Harness configuration. Replacing different generated content requires `--force`.
- `install_check.py` verifies the installed 0.4 release, wheel/native archive checksums when present, and actual isolated MCP calls. Optional `--runtime` checks the installed native plugin's eleven tools/eight skills against the official registries. It calls neither model APIs nor MATLAB and never edits a user profile.
- `doctor.py` checks Python, MATLAB executable, source hashes and, with `--run-matlab`, actually starts MATLAB and checks required toolbox functions. A static pass is not a license or numerical validation.
- `smoke.py` calls the package's public tools. Numerical operations and figures remain in MATLAB. Small Monte Carlo counts are diagnostic and must not be interpreted as publication-quality significance.

Use a new local test directory when comparing machines. Each scientific call creates a new `.acycle/runs/<run_id>` record. Do not edit the saved input or result of an existing run.

Version 0.4 exposes ten Python/MCP tools, eleven native Harness tools (including session-authorized attachment import), and eight skills. `acycle_rerun` preserves the saved analysis operation and creates a child run from an explicit parameter patch. Actual 0.4 Harness user turns verified core calling, steering and artifact delivery, with incomplete or failed dimensions: SWA additionally used forbidden NumPy numerical QA, the second PETM map failed in original MATLAB, and interpretations contained errors. Newark completed both analysis turns; the missing-metadata case asked for necessary context. See `validation/v0.4/conversation-evaluation.md` and its interpretation review. Record `passed`, `failed`, or `not_run` for each layer; these results do not establish unattended scientific reliability or GUI rendering.

Predeclared cases are in `tests/fixtures/conversation_scenarios.json`: Newark detrending, Lavernock FDR display, PETM eCOCO changes, and required clarification of missing metadata. Keep acceptance fields separate from model-visible prompts, use a new session per case, and preserve failures and recovery attempts.

The user guide includes a project-local npm runtime install, a keyless SDK mock check, and real conversation commands with explicit local paths. `needs_human_clarification` can be resumed in the same session with a predeclared, matching answer topic and a new receipt; never invent scientific facts to get a passing run. Automatic offloaded previews, optional host `read_image`/provider image input, and actual GUI display are distinct checks.

The final session-local short-handle, filename-priority and per-import source-receipt fixes have official-service fixture coverage; another real API/MATLAB conversation was not run after those fixes. Keep earlier errors and recoveries in the evidence.

The paper checks are not uniformly successful: the Lavernock peak location matches but its 5% FDR criterion is not reproduced; both the initial PETM COCO run and the independent published-log rerun lie outside the paper's declared rate interval; the Cambrian eCOCO test is a reduced workflow. Preserve these outcomes without attributing the discrepancy to version differences alone. See the current user guide and `docs/PAPER_VALIDATION.md` for numerical observations and exact scope.
