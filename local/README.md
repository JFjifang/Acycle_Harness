# Local deployment helpers

Read `../docs/USER_GUIDE.zh-CN.md` for installation and `../docs/LOCAL_HANDOFF.zh-CN.md` for a self-contained handoff prompt.

- `render_config.py` writes reviewed configuration snippets only. It never edits Codex or Harness configuration. Replacing different generated content requires `--force`.
- `doctor.py` checks Python, MATLAB executable, source hashes and, with `--run-matlab`, actually starts MATLAB and checks required toolbox functions. A static pass is not a license or numerical validation.
- `smoke.py` calls the package's public tools. Numerical operations and figures remain in MATLAB. Small Monte Carlo counts are diagnostic and must not be interpreted as publication-quality significance.

Use a new local test directory when comparing machines. Each scientific call creates a new `.acycle/runs/<run_id>` record. Do not edit the saved input or result of an existing run.

Version 0.3 exposes nine tools and eight skills. Its paper checks are not uniformly successful: the Lavernock peak location matches but its 5% FDR criterion is not reproduced; the initial PETM COCO run used a wider interval and different interpolation/correlation settings and lies outside the paper's declared rate interval; the Cambrian eCOCO test is a reduced workflow. Preserve the initial PETM failure and assess the independent published-log rerun separately, without attributing the discrepancy to version differences alone. See the current user guide and `docs/PAPER_VALIDATION.md` for numerical observations and exact scope.
