# Upstream sources and compatibility policy

Validation source: [mingsongli/acycle master](https://github.com/mingsongli/acycle), commit `dcba4279168745b563e0535b954297023dd62fc7`, README version 3.1.1. Record the actual checkout revision in every run; the branch name alone is insufficient.

The original [RobotGUI.m](https://github.com/mingsongli/acycle/blob/dcba4279168745b563e0535b954297023dd62fc7/code/guicode/RobotGUI.m) is the reference for the core workflow. At this revision its GUI defaults include lowess detrending with a 35% window, MTM spectral analysis with red-noise assessment, an evolutionary window of 35% of the series span, and wavelet analysis disabled. Old Wiki screenshots may describe different defaults. The wrapper's supported subset and explicit effective parameters are authoritative for a saved run.

Original function paths, hashes, MATLAB version and toolbox availability should be read from the MATLAB run's provenance. Where the implementation adapts a GUI callback, its source comment must explain the extraction and any deviation. Numerical parity tests compare wrapper output against independent calls to the upstream functions; successful execution or a plausible looking plot is not parity evidence.

## Updating Acycle

1. Keep the validated checkout available and obtain the candidate revision separately.
2. Check changed function signatures, defaults and toolbox dependencies for each bridged routine.
3. Run direct-call parity checks and the pinned official-example suite under MATLAB.
4. Check output axes, labels, finite values, frequency support and saved MAT/CSV/PNG files.
5. Run a negative control and at least one sensitivity branch; verify its parent run remains unchanged.
6. Store the candidate SHA and results. Only then change the validated pin.

Missing originals or incompatible signatures must produce an actionable error, never an automatic Python replacement. A changed hash is a review signal; do not claim compatibility from matching function names alone.

## Attribution

Cite Mingsong Li, Linda A. Hinnov and Lee R. Kump (2019), *Acycle: Time-series analysis software for paleoclimate research and education*, Computers & Geosciences 127, 12–22, [doi:10.1016/j.cageo.2019.02.011](https://doi.org/10.1016/j.cageo.2019.02.011). Retain original copyright and licensing notices for any extracted source. Do not infer that every external package bundled by Acycle has identical licensing terms.

Documentation references: [official examples](https://github.com/mingsongli/acycle/wiki/Examples), [mini robot](https://github.com/mingsongli/acycle/wiki/4.10-Mini-Robot), and [source README](https://github.com/mingsongli/acycle/blob/dcba4279168745b563e0535b954297023dd62fc7/README.md). Wiki URLs are orientation, not version pins.
