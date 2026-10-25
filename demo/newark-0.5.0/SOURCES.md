# Sources and scientific scope

## Exact input and units

The bundled file is copied byte for byte from `data/Examples/Example-LateTriassicNewarkDepthRank.txt` in [Acycle commit dcba4279168745b563e0535b954297023dd62fc7](https://github.com/mingsongli/acycle/tree/dcba4279168745b563e0535b954297023dd62fc7). It has SHA-256 `1cd82c19c0de98a8c4d6f09d3af1fdb3ff2e07fe93c3ee241102dd75e4b65ac2` and 39,218 bytes. Its CR line endings are preserved. The existing MATLAB baseline reports 2,344 observations at 0–1999.60992 m and median spacing 0.85344 m.

The [original GUI callback](https://github.com/mingsongli/acycle/blob/dcba4279168745b563e0535b954297023dd62fc7/code/guicode/AC.m#L9097), `menu_example_Newark_Callback`, loads this exact filename and labels its axes `Depth (m)` and `Depth Rank`. Thus metres are sourced metadata, not guessed from the numbers. The [official Acycle v2.8 User's Guide](https://acycle.org/docs/Acycle_Users_Guide.pdf), printed p.38, identifies this exact file as the Newark Basin depth-rank example of Olsen and Kent (1996).

Olsen, P. E., and Kent, D. V. (1996). *Milankovitch climate forcing in the tropics of Pangaea during the Late Triassic*. Palaeogeography, Palaeoclimatology, Palaeoecology 122, 1–26. [DOI](https://doi.org/10.1016/0031-0182(95)00171-9).

We have not established the exact core/composite-section origin, orientation relative to absolute age, or a row-by-row mapping between this example and published age-control horizons. The filename alone does not supply those constraints. Cite Acycle and the original study when reusing the example. This package does not assign a new licence to the historical observations or redistribute the journal articles.

## External prior for the long cycle

Kent, D. V., and Olsen, P. E. (1999). *Astronomically tuned geomagnetic polarity timescale for the Late Triassic*. Journal of Geophysical Research: Solid Earth 104(B6), 12831–12841. [DOI and publisher abstract](https://doi.org/10.1029/1999JB900076).

The abstract describes a roughly 5,000-m composite Newark section and states that its prominent 404-kyr eccentricity cycle has a mean thickness of about 60 m. This is the external basis for centring this demonstration's depth filter near 60 m. The 48–80 m nominal band is a declared teaching choice; it is not a confidence interval or a filter specification reproduced from that paper. The paper's long-cycle assignment is itself part of an astronomical calibration, not an independent determination that every 60-m feature in our example is orbital.

Kent, D. V., et al. (2018). *Empirical evidence for stability of the 405-kiloyear Jupiter–Venus eccentricity cycle over hundreds of millions of years*. PNAS 115(24), 6153–6158. [DOI](https://doi.org/10.1073/pnas.1800891115); [open full text](https://pmc.ncbi.nlm.nih.gov/articles/PMC6004457/).

Independent U–Pb zircon dates from the Chinle Formation, linked by magnetostratigraphy to the Newark–Hartford timescale, support the stability of the 405-kyr pacing back to at least about 215 Ma. This supports a regional astronomical hypothesis. It does not locate the supplied two-kilometre excerpt in absolute time or prove that an automatically selected filter extremum has the correct cycle number or phase. We use the modern nominal 405 kyr as an explicit assumption, rather than claiming to reproduce the 1999 paper's exact 404-kyr calibration.

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

This package supplies source-backed data, a declared demonstration protocol and natural-language conversation prompts. The earlier 0.4 real Harness Newark session exercised depth-domain analysis and a detrending change, not this full chronology workflow. Source-code availability, successful file delivery, actual numerical execution, scientific interpretation and visible client rendering are separate evidence. A current rehearsal must record each relevant outcome rather than inheriting an assumed pass from the design.
