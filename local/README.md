# Local deployment helpers

Read `../docs/USER_GUIDE.zh-CN.md` for installation and `../docs/LOCAL_HANDOFF.zh-CN.md` for a self-contained handoff prompt.

- `render_config.py` writes reviewed configuration snippets only. It never edits Codex or Harness configuration. Replacing different generated content requires `--force`.
- `doctor.py` checks Python, MATLAB executable, source hashes and, with `--run-matlab`, actually starts MATLAB and checks required toolbox functions. A static pass is not a license or numerical validation.
- `smoke.py` calls the package's public tools. Numerical operations and figures remain in MATLAB. Small Monte Carlo counts are diagnostic and must not be interpreted as publication-quality significance.

Use a new local test directory when comparing machines. Each scientific call creates a new `.acycle/runs/<run_id>` record. Do not edit the saved input or result of an existing run.

Version 0.4 exposes ten Python/MCP tools, eleven native Harness tools (including session-authorized attachment import), and eight skills. `acycle_rerun` preserves the saved analysis operation and creates a child run from an explicit parameter patch. The new Harness workflow must be checked with separate, short user turns, attachment import, official image/file delivery events, and actual client viewing. Record `passed`, `failed`, or `not_run` for each layer. Earlier model/tool loops and registry smoke tests do not establish this complete workflow; real 0.4 conversation acceptance is still in progress.

Predeclared cases are in `tests/fixtures/conversation_scenarios.json`: Newark detrending, Lavernock FDR display, PETM eCOCO changes, and required clarification of missing metadata. Keep acceptance fields separate from model-visible prompts, use a new session per case, and preserve failures and recovery attempts.

The paper checks are not uniformly successful: the Lavernock peak location matches but its 5% FDR criterion is not reproduced; both the initial PETM COCO run and the independent published-log rerun lie outside the paper's declared rate interval; the Cambrian eCOCO test is a reduced workflow. Preserve these outcomes without attributing the discrepancy to version differences alone. See the current user guide and `docs/PAPER_VALIDATION.md` for numerical observations and exact scope.
