# MATLAB-first execution contract

The Harness plugin and Python package are an orchestration layer around a real MATLAB process. Production numerical analysis and figures are produced in MATLAB, using Acycle's original functions wherever a callable function exists. Python may inspect file metadata, validate tool arguments, invoke MATLAB, transport files, index runs and format JSON responses. It must not silently replace MATLAB with SciPy, NumPy, Octave, or an approximate spectrum.

## Execution

1. The model calls `acycle_capabilities` and `acycle_inspect` to establish the available backend and input.
2. `acycle_analyze` creates a distinct run, writes a JSON request, and invokes the MATLAB entry point.
3. MATLAB loads the numerical series, cleans/interpolates/detrends it, calls Acycle routines, generates figures and saves numerical output.
4. Python returns the MATLAB response and a durable run identifier. `acycle_get_run` reopens that result.
5. `acycle_sensitivity` changes one parameter across a set of new runs. `acycle_compare` exposes their saved results; it does not generate a replacement Python spectrum or plot.

Select local execution with `ACYCLE_BACKEND=local`, `ACYCLE_ROOT` pointing to the Acycle checkout, and `MATLAB_EXECUTABLE` if MATLAB is not on PATH. `ACYCLE_BACKEND=github` uses the configured `ACYCLE_GITHUB_REPO` and `ACYCLE_GITHUB_REF`. Remote execution uploads the selected dataset to that repository's workflow. Use a repository whose visibility and access are appropriate for the data.

## Acycle compatibility boundary

Upstream source is an external checkout, pinned for validation; the package does not vendor the whole Acycle application. A MATLAB wrapper may extract a computation from a GUI callback when no headless API exists, but must identify the original file, revision, procedure and intentional differences. General-purpose MATLAB plotting around Acycle outputs is acceptable: the plotting backend remains MATLAB and the figures must not be misrepresented as pixel-identical copies of the GUI.

Do not equate headless workflow coverage with full Acycle GUI compatibility. Features not exposed by the adapter remain unsupported. A later Acycle version can be tried, but its changed function hashes and parity tests must be reviewed before declaring it validated. See [UPSTREAM_COMPATIBILITY.md](UPSTREAM_COMPATIBILITY.md).

## Extending a user's research task

For a requested operation absent from Acycle, first compose existing tools or write a small MATLAB adapter calling the installed original code. Python is allowed for an additional capability Acycle does not implement, file conversion, or a user-specific exploratory extension. Record that extension explicitly. Whenever its output feeds spectral analysis, filtering, time conversion, or publication figures, save an inspectable intermediate dataset and bridge it back to MATLAB. Never conceal a backend change in a run label.

## Scientific interpretation

Pointwise red-noise confidence curves do not establish family-wise significance, astronomical origin, or a valid age model. Filtering a selected band cannot independently confirm that band. A time conversion requires stated units and an explicit sedimentation rate or age-depth model. Preserve these assumptions, source hashes and the parent run when a user steers the analysis.
