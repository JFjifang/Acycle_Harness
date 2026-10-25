# Harness 0.5.1 adaptation checks

`SUMMARY.json` is the final installed-package receipt. It binds the Python wheel,
native tarball, fresh npm lockfile, four actual agent-composition receipts and the
public Newark skill/source hashes. The verified official release is
`0.2.1-rc.3`; npm's `latest` tag still points at `0.2.1-rc.2`, while `next` and the
newest published GitHub release are `0.2.1-rc.3`. `upstream-release.json` records
the release tag's commit separately from the newer default-branch snapshot.

The four `*-installed.json` checks used an independently installed 0.5.1 Python
wheel and the final native tarball, without `PYTHONPATH` or `PYTHONHOME`. All
16 tarball files match the three installed native copies byte for byte. Normal
Web and Desktop configurations have 13 native tools and 10 Acycle skills; both
explicit Newark configurations have the same 13 tools and 11 scoped skills.
The actual agent loads the persona, skill bodies and catalog, `read_image`, and
`present`. Its official `deepseek-flash` route resolves text/image capability.
A deterministic local adapter captures the model-facing catalog; no model API
or MATLAB execution occurs.

The Desktop checks mount the actual installed native bundle declaration and
the generated `desktop.preset.patch.yml` using the published shared Web host,
preset registry and agent services. The fixture supplies the official model
selection separately, as the user's existing Desktop model settings would.
It passes no Acycle/MATLAB backend environment from the host: the generated
preset's child configuration supplies the Python executable, Acycle checkout,
local backend and MATLAB executable path. The latter is a deliberately
unavailable example macOS path; `matlab_available: false` is expected here.
These checks establish the shared plugin composition, not Electron startup,
the Desktop installation UI, macOS rendering or local MATLAB readiness.

`node-contracts-installed.tap` contains 28 passing tests with no skips. They
exercise the official attachment/session/presentation services, method support,
failure/cancellation handling, mandatory workflow policy and child-only MATLAB
environment transport. The command used is:

```sh
env -u PYTHONPATH -u PYTHONHOME \
  ACYCLE_PYTHON=/workspace/acycle-release-check-v051/bin/python \
  ACYCLE_HARNESS_RUNTIME=/workspace/acycle-runtime-v051 \
  node --test --test-isolation=none --test-reporter=tap \
  plugin/tests/*.test.mjs tests/test_harness_conversation_support.mjs
```

Earlier `*-source.json` and `node-contracts.tap` receipts used the source tree
through `PYTHONPATH` during development. The initial
`desktop-shared-normal-source.json` failure is retained: that fixture declared
the bundle but omitted the profile-local package installation. Installing the
tarball into the fixture profile, as a real Desktop installation does, resolved
the missing plugin. `desktop-shared-normal-installed-source.json` records the
successful correction. The final `*-installed.json` records supersede these
development checks for release acceptance.
