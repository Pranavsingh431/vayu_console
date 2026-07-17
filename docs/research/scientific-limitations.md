# Scientific Limitations

> What Vayu Console can and cannot claim, and why.
>
> Written to be read adversarially. If an atmospheric scientist audits this project, this
> is the document that decides whether the rest survives. Every limitation here is one we
> found by testing, not one we anticipated — which is itself a warning about the ones we
> have not found yet.

Last updated 2026-07-17, end of the Phase 1 data spike.

---

## 1. The one that matters most: we have no ground truth for attribution

**We cannot measure how much of Delhi's PM2.5 came from any given source.** Nothing in our
data does this, and nothing available to us could.

- FIRMS detects **thermal anomalies from orbit** — a fire existed at a place and time. It
  does not measure emissions, and it says nothing about what reached a monitor 200 km away.
- CPCB/OpenAQ measure **mass concentration at a point**. They do not carry chemical
  speciation or isotopic markers, so a measurement cannot be decomposed into sources.
- No receptor-model input (PMF, CMB) is available to us — that needs filter-based speciated
  sampling we do not have.

**Therefore every attribution this system produces is inference under stated assumptions,
never measurement.** The system may say _"conditions are consistent with a large stubble
contribution: wind from 315° at 4 m/s, 1,604 fires upwind within 12 hours, boundary layer
at 210 m."_ It must never say _"stubble contributed 44%."_

This is not a hedge. It is the difference between a defensible tool and a fabricated one.
Any UI, phrasing, or API field implying measured apportionment is a bug.

**Available cross-check, not validation:** NCAP/PRANA publishes source-apportionment
percentages for Delhi. Agreeing with a published study is a sanity check on plausibility.
It does not make our number measured, and their study's assumptions become ours the moment
we lean on it.

---

## 2. Diwali is confounded with stubble burning — permanently

Diwali follows the lunar calendar and lands in October–November: **exactly the
paddy-residue burning window**. This is not bad luck in one year; it is structural.

Measured on the Phase 1 gate day (27 October 2019):

| Signal                                        | Value                        |
| --------------------------------------------- | ---------------------------- |
| PM2.5, Burari, 15:30 IST                      | 61 µg/m³                     |
| PM2.5, Burari, 23:30 IST                      | **1,288 µg/m³** (peak 1,357) |
| VIIRS fire detections, same day, stubble belt | **1,604**                    |

Both explanations are live simultaneously. Any Diwali analysis that ignores fire counts is
wrong, and any stubble analysis during Diwali week that ignores fireworks is equally wrong.

**Why we chose this event as the gate anyway:** it is the officer's actual question. _"Is
tonight's spike fireworks or Punjab?"_ If the pipeline cannot even represent the confound,
we learn it in Phase 1 rather than Phase 3.

**Partial escape:** Odd-Even II (15–30 April 2016) sits outside both stubble season and
winter inversion. It is the only window in our data where a vehicular signal is not
confounded by transport. It has only 11 stations.

---

## 3. Data provenance and its holes

### 3.1 The 2023–2024 gap

Delhi stations with data in the OpenAQ S3 archive, per year:

| 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023  | 2024  | 2025 | 2026 |
| ---- | ---- | ---- | ---- | ---- | ---- | ---- | ---- | ----- | ----- | ---- | ---- |
| 7    | 11   | 10   | 66   | 46   | 51   | 51   | 50   | **1** | **2** | 55   | 63   |

**No trend line may be drawn across 2023–2024.** Any multi-year analysis must either stop
at 2022, start at 2025, or show the discontinuity explicitly. Interpolating across it would
invent two years of data.

### 3.2 One physical station appears under several OpenAQ location ids

**21 of 96 Delhi sites are fragmented across 2–3 location ids**, each holding a different
slice of time. Anand Vihar:

| location id | provider | years present in the archive |
| ----------- | -------- | ---------------------------- |
| 235         | CPCB     | 2015–2018, 2025–2026         |
| 10487       | caaqm    | 2018–2021                    |
| 5509        | caaqm    | 2018, 2021–2022              |

This cuts both ways, and both are dangerous:

1. **Double counting.** 2018 appears under all three ids. Ingesting every location id and
   averaging makes Anand Vihar vote three times in any city-wide mean for 2018 — silently
   weighting the average toward whichever sites happen to be duplicated. Roadside sites
   like Anand Vihar are among the most duplicated _and_ the most polluted, so the bias is
   upward, not random.
2. **Phantom gaps.** No single id spans 2015–2022, so a per-id coverage report calls 48 of
   96 stations "gappy". Merged, the major sites are nearly continuous. The naive report
   understates our data.

**Neither problem affects the Diwali 2019 gate:** all 46 location ids with 2019 data are
distinct physical sites, verified — zero duplication in that year.

**Required before any cross-year analysis:** resolve location ids to physical sites (name
and coordinates, not id) and pick one id per site per period. Not yet implemented.

### 3.3 Station composition changes, so city means are not comparable across years

7 stations in 2015, 66 in 2018, 46 in 2019. A "Delhi average" is an average **over whichever
stations existed**, and those stations differ in siting — roadside, industrial, background.
A rise from 2015 to 2018 may be entirely composition.

**Rule:** never compare a city-wide mean across years without either fixing the station set
or stating the composition. Prefer a fixed panel of stations present in both periods.

### 3.4 Live and historical are different measurements

- `data.gov.in` returns **`min_value` / `max_value` / `avg_value`** aggregates per pollutant.
- The S3 archive returns **raw individual readings**.

These are not the same quantity. Joining them into one series across the present boundary,
without saying so, produces a discontinuity that is an artefact of our plumbing, not of
Delhi's air. The `source` column exists on every row for exactly this reason.

### 3.5 Sampling is irregular, not hourly

Observed timestamps at a real station: 00:15, 00:30, 01:00, 01:30, 02:00, 02:15, 02:45.
Gaps are the norm.

Anything assuming a fixed cadence — a "missing hours" count, a naive resample, a
completeness percentage against 24 — is wrong. Report the **observed** interval and the true
observation count behind every aggregate.

### 3.6 Timezone

The archive publishes **IST (+05:30)**, and a day file runs past midnight IST (the
`20191027` file contains `2019-10-28T00:00:00+05:30`). Diwali's firework peak is at night
IST. **Reading these as UTC shifts the peak by 5.5 hours and attributes it to the wrong
day** — which, for an event defined by a single evening, inverts the conclusion.

We store UTC and present IST. Every date boundary in an analysis must be an IST boundary.

---

## 4. Instrument and measurement caveats

- **Outliers are the signal.** On Diwali night PM2.5 legitimately exceeds 1,300 µg/m³.
  Standard outlier removal deletes precisely the events this project exists to study. Our
  validator reports outliers and never removes them.
- **Stuck sensors read as valid data.** A monitor repeating one value all day passes every
  range check. Detected via zero variance, not by range.
- **Reference-grade vs low-cost.** OpenAQ carries CPCB reference monitors _and_ AirGradient
  low-cost sensors in Delhi. These have different uncertainty; mixing them into one mean
  without weighting is unsound. Filter by provider.
- **Confidence scales are not comparable.** VIIRS reports `l`/`n`/`h`; MODIS reports 0–100.
  We store the raw string rather than coercing them into one number, because collapsing two
  different scales invents precision that does not exist.

---

## 5. Meteorology caveats

- **ERA5 cells are ~25 km.** Delhi is roughly two cells across. A "wind direction for Delhi"
  is a cell average and cannot resolve street-canyon or local circulation.
- **Boundary layer height is modelled, not observed.** It is a reanalysis product with real
  uncertainty, and it is the single most influential variable in any dispersion argument —
  the same emissions read as 80 or 400 µg/m³ depending on it. Uncertainty in BLH propagates
  directly into any attribution.
- **Station anemometers are better where they exist** (~46 Delhi sites): they measure the air
  that actually reached the monitor. Prefer them; fall back to reanalysis.

---

## 6. Satellite caveats _(untested — flagged, not verified)_

TROPOMI NO₂ requires `qa_value > 0.75`, and retrievals degrade under cloud and heavy
aerosol. Delhi's winter haze is heavy aerosol. **We expect the satellite to go blind exactly
when pollution is worst** — i.e. during every episode we care about.

This is stated from domain knowledge and has **not** been verified against Delhi data. It
must be tested before any Phase 3 claim leans on TROPOMI. Given §1, its likely role is
corroborating a spatial gradient, not quantifying anything.

---

## 7. What the system may and may not say

| ✅ Defensible                                                                   | ❌ Not defensible                                   |
| ------------------------------------------------------------------------------- | --------------------------------------------------- |
| "PM2.5 at Anand Vihar rose from 61 to 1,288 µg/m³ between 15:30 and 23:30 IST." | "Fireworks caused a 1,227 µg/m³ rise."              |
| "1,604 fires were detected upwind within 12 hours, with wind at 315°/4 m/s."    | "Stubble contributed 44% of tonight's PM2.5."       |
| "Conditions resemble 4 Nov 2019, when GRAP III was invoked."                    | "This intervention will reduce PM2.5 by 18%."       |
| "Boundary layer at 210 m is in the lowest decile for October."                  | "Low mixing height is responsible for the episode." |
| "We have no reliable data for 2023–2024."                                       | _(silently interpolating across it)_                |

The right-hand column is not a list of things to phrase more carefully. It is a list of
claims the data cannot support at all.

---

## 8. Known unknowns

Things that could still invalidate parts of the project, in rough order of risk:

1. **Ward boundaries and OSM are untested.** Ward aggregation is on the Diwali 2019 critical
   path and we have not yet verified a source, its CRS, or its vintage.
2. **NCAP/PRANA extraction is untested.** It is a PDF; table extraction may not be clean.
3. **TROPOMI is untested** (§6).
4. **We have not verified whether the 44 live data.gov.in stations reconcile with the 96
   OpenAQ locations.** Names differ; there is no shared id. If they do not reconcile, live
   and historical views show different cities. §3.2 makes this harder: OpenAQ's own ids do
   not reconcile with each other either.
5. **Location-id deduplication is not implemented** (§3.2). Every cross-year aggregate is
   wrong until it is.
6. **Diwali 2025's exact date is unconfirmed** in our natural experiment table.
7. **We have not yet tested a full stubble season ingest** — 2 months × ~50 stations is a far
   larger volume than the 15-day Diwali window, and FIRMS' 5,000/10-min quota has not been
   stressed.
