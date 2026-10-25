---
name: acycle-coco
description: Estimate and test sedimentation-rate candidates with original Acycle COCO or eCOCO MATLAB methods and reproducible target, window and Monte Carlo choices.
---

Use `acycle_coco` for a full-record or sliced COCO request and `acycle_ecoco` for evolutionary windows. These tools call the pinned Acycle v2 scientific cores; a paper using an earlier implementation is not automatically numerically equivalent. All calculations, Monte Carlo simulations and figures run in MATLAB. Python only sends parameters, preserves inputs and collects artifacts.

Require `depth_unit` and explicit `sedimentation_rate_min`, `sedimentation_rate_max`, `sedimentation_rate_step`, all rates in cm/kyr. State the geological basis for the range. Supply exactly one of `middle_age_ma` or `orbital_periods_kyr`; the former invokes Acycle's original age-dependent period calculation, the latter declares explicit periods in kyr. Do not invent the age to force a preferred optimum. Keep coordinate depth units, age in Ma, periods in kyr and rate in cm/kyr distinct.

COCO `method: adaptive` maps to original adaptive9b and requires nine periods; `phase_averaged` maps to original adaptive and accepts 2–32 periods. eCOCO supports `adaptive`, `blocked` and `interleaved`, requires nine periods, and requires `window`/`step` in input depth units. Preserve unsupported/invalid-window information, and do not infer a continuous rate history across failed windows. The bridge uses complete windows without synthetic edge padding. Global nonlinear detrending is unavailable for blocked/interleaved modes because it would mix held-out information.

Inspect the current schema for optional detrending, `nfft`, `max_frequency`, `correlation`, `red_noise`, `nsim`, `seed`, and COCO-only `slices`. Record effective parameters. Default 199 simulations and local smoke settings such as 19 simulations are not interchangeable with a publication's Monte Carlo design. Choose simulation count from the required tail resolution and computational budget, not from the desired significance. A fixed seed makes runs reproducible; it does not remove Monte Carlo uncertainty.

Read original output labels and method notes to distinguish correlation, pointwise p-values, search/global statistics, target support and any held-out criterion. Never relabel a pointwise result as control over all rates, windows and parameter choices. The largest correlation need not be the most defensible chronology. Compare with independent age constraints and report alternative optima.

Use immutable parent-linked runs when changing one parameter. Compare grid ranges, spacing, targets, detrending, windows, red-noise choices and Monte Carlo count. Preserve a declared baseline before exploratory steering. For paper tasks, obtain the full distribution's `benchmarks/` source records or the repository at https://github.com/JFjifang/Acycle_Harness/tree/main/benchmarks; verify the exact interval, columns and hashes. Report separately the original-function parity, authentic-data workflow, matched published quantitative criterion, and remaining differences.
