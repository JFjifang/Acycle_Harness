# Sources and scientific scope

## Exact input and units

The bundled file is copied byte for byte from `data/Examples/Example-LateTriassicNewarkDepthRank.txt` in [Acycle commit dcba4279168745b563e0535b954297023dd62fc7](https://github.com/mingsongli/acycle/tree/dcba4279168745b563e0535b954297023dd62fc7). It has SHA-256 `1cd82c19c0de98a8c4d6f09d3af1fdb3ff2e07fe93c3ee241102dd75e4b65ac2` and 39,218 bytes. Its CR line endings are preserved. The existing MATLAB baseline reports 2,344 observations at 0–1999.60992 m and median spacing 0.85344 m.

The [original GUI callback](https://github.com/mingsongli/acycle/blob/dcba4279168745b563e0535b954297023dd62fc7/code/guicode/AC.m#L9097), `menu_example_Newark_Callback`, loads this exact filename and labels its axes `Depth (m)` and `Depth Rank`. Thus metres are sourced metadata, not guessed from the numbers. The [official Acycle v2.8 User's Guide](https://acycle.org/docs/Acycle_Users_Guide.pdf), printed p.38, identifies this exact file as the Newark Basin depth-rank example of Olsen and Kent (1996).

Olsen, P. E., and Kent, D. V. (1996). *Milankovitch climate forcing in the tropics of Pangaea during the Late Triassic*. Palaeogeography, Palaeoclimatology, Palaeoecology 122, 1–26. [DOI](https://doi.org/10.1016/0031-0182(95)00171-9).

We have not established the exact core/composite-section origin, orientation relative to absolute age, or a row-by-row mapping between this example and published age-control horizons. The filename alone does not supply those constraints. Cite Acycle and the original study when reusing the example. This package does not assign a new licence to the historical observations or redistribute the journal articles.

## Early recognition: about 400 kyr was not originally an exact 405-kyr measurement

Olsen, P. E. (1984). *Periodicity of lake-level cycles in the Late Triassic Lockatong Formation of the Newark Basin (Newark Supergroup, New Jersey and Pennsylvania)*. In *Milankovitch and Climate*, Part 1, 129–146. [Author-hosted original](https://www.ldeo.columbia.edu/~polsen/nbcp/olsen_84.pdf), printed pp.129 and 144.

This early primary account relates short lake-level cycles and their larger bundles through approximately 1:5:20 thickness ratios. It estimates a long cycle near 418 kyr from the contemporary calibration and interprets the hierarchy in terms of precession and eccentricity. It is an early directly checked source, not a claim that no earlier discussion exists. Van Houten's earlier recognition of sedimentary cycles should not be relabelled as a precise measurement of the modern 405-kyr term.

Olsen, P. E. (1986). *A 40-million-year lake record of early Mesozoic orbital climatic forcing*. Science 234(4778), 842–848. [DOI](https://doi.org/10.1126/science.234.4778.842), [indexed original abstract](https://pubmed.ncbi.nlm.nih.gov/17758107/), [author-hosted original](https://www.ldeo.columbia.edu/~polsen/nbcp/olsen_86_science.pdf).

The classic Science paper develops the spectral and cycle-hierarchy evidence for an approximately 400-kyr component. Its thickness scales belong to its studied sections; they are not universal fixed wavelengths for every Newark excerpt.

The [author-hosted Olsen and Kent (1996) original](https://www.ldeo.columbia.edu/~polsen/nbcp/olsen.and.kent.ppp.96.pdf), abstract on printed p.1, combines FFT, multitaper and joint time–frequency analysis of the depth-rank record. It discusses a hierarchy including a long eccentricity term then stated as 412.9 kyr. The 1984/1986/1996 values must not be silently rewritten as measurements of exactly 405 kyr. The useful methodological cue is to inspect related wavelength groups and their persistence along the section before assigning an orbital interpretation.

## External prior for the long cycle

Kent, D. V., and Olsen, P. E. (1999). *Astronomically tuned geomagnetic polarity timescale for the Late Triassic*. Journal of Geophysical Research: Solid Earth 104(B6), 12831–12841. [DOI and publisher abstract](https://doi.org/10.1029/1999JB900076).

The abstract describes a roughly 5,000-m composite Newark section and states that its prominent 404-kyr eccentricity cycle has a mean thickness of about 60 m. This is the external basis for centring this demonstration's depth filter near 60 m. The 48–80 m nominal band is a declared teaching choice; it is not a confidence interval or a filter specification reproduced from that paper. The paper's long-cycle assignment is itself part of an astronomical calibration, not an independent determination that every 60-m feature in our example is orbital.

Kent, D. V., et al. (2018). *Empirical evidence for stability of the 405-kiloyear Jupiter–Venus eccentricity cycle over hundreds of millions of years*. PNAS 115(24), 6153–6158. [DOI](https://doi.org/10.1073/pnas.1800891115); [open full text](https://pmc.ncbi.nlm.nih.gov/articles/PMC6004457/).

Independent U–Pb zircon dates from the Chinle Formation, linked by magnetostratigraphy to the Newark–Hartford timescale, support the stability of the 405-kyr pacing back to at least about 215 Ma. This supports a regional astronomical hypothesis. It does not locate the supplied two-kilometre excerpt in absolute time or prove that an automatically selected filter extremum has the correct cycle number or phase. We use the modern nominal 405 kyr as an explicit assumption, rather than claiming to reproduce the 1999 paper's exact 404-kyr calibration.

## Original COCO paper and the modern bridge

Li, M., Kump, L. R., Hinnov, L. A., and Mann, M. E. (2018). *Tracking variable sedimentation rates and astronomical forcing in Phanerozoic paleoclimate proxy series with evolutionary correlation coefficients and hypothesis testing*. Earth and Planetary Science Letters 501, 165–179. [DOI](https://doi.org/10.1016/j.epsl.2018.08.041), [author-hosted original](https://www.meteo.psu.edu/holocene/public_html/Mann/articles/articles/LiEtAl_EPSL18.pdf).

Read §2 and §4.2, especially Figs.5B, 6C and 9. The paper jointly evaluates correlation, the null test and participating astronomical terms; competing rate branches must be compared using all three. Sliding windows address changing accumulation and signal quality. Its 0–2000 m record is a Rutgers–Somerset–Weston–Martinsville composite, but this does not establish byte or row identity with the bundled Acycle example.

| Setting | 2018 Newark example | This demonstration |
| --- | --- | --- |
| Trend | 500-m robust LOESS (`rloess`) | 35% LOWESS; these are different smoothers |
| Target/correlation | La2004, 202–204 Ma; Pearson | Modern coherent nine-term Adaptive target at approximate 210 Ma; Spearman |
| Background/slices | AR(1) spectral subtraction; two-slice COCO | `red_noise: 0`; one-slice COCO |
| Rate grid (cm/kyr) | 1–30, step 0.2 | 5–25, step 1 |
| eCOCO window/step (m) | 100/5.1 | 600/100 |
| Monte Carlo budget | 2000 | 19, exploratory only |

These differences are intentional retained settings from the preceding demonstration, not an attempted numerical reproduction of the paper. `red_noise: 0` disables background-spectrum subtraction, not Monte Carlo testing; the modern bridge's null construction and rate-global correction also differ from the historical algorithm. The bridge does not expose the historical `rloess` preprocessing or the complete original La2004 target-series workflow. Setting `Pearson` alone cannot restore them. A later paper-oriented comparison must retain the baseline, list supported substitutions, run a new MATLAB branch, and preserve an inconclusive result. Published best rates or p-values are never acceptance targets.

## Research cues supplied to the model

Use the papers to pose checks, rather than to supply the desired answer: Does the untreated depth record contain a related hierarchy of scales? Does the evolutionary spectrum show persistent bands or frequency drift? Does detrending remove long background variation without erasing the candidate band? At a candidate rate, are the relevant terms actually resolvable, and does the corrected null test support the interpretation? Are eCOCO ridges stable under the requested window comparison? These questions motivate the existing MATLAB workflow without changing its declared settings.

For the long-cycle hypothesis, inspect the actual bandpassed curve and its extrema before constructing controls. Weak subsidiary extrema, edge behavior or gaps can produce extra or missing cycles. If the declared band does not yield defensible controls, describe the relative chronology as unresolved; do not adjust the band until a desired age or cycle count appears. The unfiltered original proxy, transformed with the actual controls, supplies the subsequent time-domain diagnostic.

## Upstream software precedents for age and rate search

The following are source-code settings in the pinned Acycle tree, not independent dating evidence:

| Source | Data used there | Settings |
| --- | --- | --- |
| [runCocoPublicationValidation.m](https://github.com/mingsongli/acycle/blob/dcba4279168745b563e0535b954297023dd62fc7/code/corrcoef/runCocoPublicationValidation.m) | `Example-LateTriassicNewarkDepthRank_0_800-300-LOWESS.txt` | 210 Ma; 5–25 cm/kyr, step 0.05; expected range 10–15 cm/kyr |
| [runCocoEightMethodExperiment.m](https://github.com/mingsongli/acycle/blob/dcba4279168745b563e0535b954297023dd62fc7/code/corrcoef/runCocoEightMethodExperiment.m) | `newark2km-s-rsp0.85.txt` | 210 Ma; 1–40 cm/kyr, step 0.1; reference approximately 15 cm/kyr; 12–18 comparison interval |
| [runEcocoTwoMethodExperiment.m](https://github.com/mingsongli/acycle/blob/dcba4279168745b563e0535b954297023dd62fc7/code/corrcoef/runEcocoTwoMethodExperiment.m) | `newark2km-s-rsp0.85.txt` | 210 Ma; 1–40 cm/kyr, step 0.1; reference 15 cm/kyr; window based on two long cycles |
| [runSyn3FourMethodPublicationStudy.m](https://github.com/mingsongli/acycle/blob/dcba4279168745b563e0535b954297023dd62fc7/code/corrcoef/runSyn3FourMethodPublicationStudy.m) | `newark2km-s-rsp0.85.txt` | 210 Ma; 1–30 cm/kyr, step 0.2; reference 15 cm/kyr |

The demo uses 210 Ma only to select approximate age-dependent orbital targets, and 5–25 cm/kyr as an exploratory search range. Its 1 cm/kyr rate spacing, 19 simulations and 600-m complete eCOCO windows are separately disclosed choices. The full example retains its own 0.85344-m grid; it is not silently rebuilt at 0.85 m to mimic the differently named upstream record. The old 8–16 cm/kyr smoke interval is not used as a published Newark constraint.

The earlier v0.4 Newark depth-spectrum results were known while designing this workflow. The literature supplies an external reason for the fixed band, but this demonstration is not a blinded or independently preregistered detection study. Its modern Adaptive target and null model also differ from historical paper implementations. Monte Carlo inference is conditional on the globally LOWESS-transformed record; the nonlinear trend is not refit in every null realization.

The complete demo first uses original Interpolation Pro with linear interpolation, the 0.85344-m grid reported by the existing MATLAB baseline, and no extrapolation. Depth-domain MTM/EvoFFT, COCO and eCOCO all use that same newly generated MATLAB grid artifact. The filtered series and controls descend from this branch. The final time-domain analysis returns to the untouched original proxy with those controls. The raw source and reformatted/interpolated artifact have separate hashes and explicit lineage; equality of their byte hashes is not expected.

The regional mean thickness and long-cycle period imply a rough scale of 15 cm/kyr, but that conversion is conditional on the orbital assignment. It is useful context, not an independently validated rate for this particular dataset. The demo must not score success by selecting a result close to that value.

## Tuning implementation and interpretation

The official guide's printed pp.79–80 documents **Build Age Model**: assign consecutive filtered maxima or minima to a supplied cycle period. Printed pp.129–131 demonstrates this operation and subsequent **Age Scale** on Wayao data, explicitly beginning with an assumed cycle assignment. That is a documented Acycle workflow, not a Newark-specific chronology recipe.

Our demonstration follows that operation with explicitly chosen 405-kyr maximum-to-maximum controls, first selected maximum at relative time zero, and trimming outside the control range. MATLAB must extract the actual extrema, build controls and apply Acycle tuning/interpolation. The relative coordinate increases with the supplied depth coordinate; it is not labelled as an absolute age before present. The time-domain diagnostic uses the original proxy after applying those same controls. It does not analyse the band-pass curve and call the imposed peak an independent success.

Neither phase sensitivity nor a visually smooth rate curve supplies a formal age confidence interval. A continuous model may be inappropriate across an unresolved hiatus or a missing cycle. An all-NaN eCOCO map, insufficient extrema or nonmonotone control table must remain visible as an unresolved/failed stage, with any repair preserved as a new run.

## What this package establishes

This 0.5.1 package adds checked literature context and a revised short prompt while retaining the 0.5.0 numerical presets. The 0.5.0 two-turn rehearsal and its original results remain historical evidence in `REHEARSAL.zh-CN.md`; they do not prove that the revised prompt has been replayed or that the literature has been reproduced. `literature_sources.json` records the checked source URLs, PDF digests and inspected locations; journal PDFs are not redistributed. Source-code availability, successful file delivery, actual numerical execution, scientific interpretation and visible client rendering are separate evidence. A current rehearsal must record each relevant outcome rather than inheriting an assumed pass from the design.
