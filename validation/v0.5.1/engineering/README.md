# Engineering evidence

`python-tests.txt`: 203 Python tests passed. No new MATLAB calculations or model API calls.

`python-build.txt`: standard isolated PEP 517 build produced the final 0.5.1 wheel and source archive. The earlier optional `--no-isolation` attempt is retained in `python-build-no-isolation.txt`; that development environment did not contain setuptools. The standard isolated build installed its declared build dependencies and completed normally.

`npm-pack.txt`: native 0.5.1 package construction. Package bytes, independent installation, actual MCP and official Harness registration are checked in `../release-verification.json`.

The official runtime plugin contracts, actual agent composition and their scope are recorded under `../harness/`. The actual browser fixture in `../web/` reopens existing MATLAB outputs, checks main Chat images and verifies downloaded bytes. It does not ask a model to interpret the figures or rerun scientific calculations.
