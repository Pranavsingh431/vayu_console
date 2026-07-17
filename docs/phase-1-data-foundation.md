# Phase 1 — Data Foundation

> **Status:** revised 2026-07-17, after the data spike. **This document supersedes the
> original Phase 1 specification.** Where the two disagree, this one is correct: it is
> written from measured behaviour, not from documentation.
>
> Every claim below marked ✅ was verified by a real request against a real endpoint. Claims
> without that marker are design intent and must not be trusted until tested.

---

## 1. Why this document exists

The original Phase 1 spec assumed:

| Original assumption                        | Reality                                                                                               |
| ------------------------------------------ | ----------------------------------------------------------------------------------------------------- |
| CPCB history comes from data.gov.in        | ❌ data.gov.in is a **live snapshot with zero history**                                               |
| OpenAQ is a "historical backup / fallback" | ⚠️ Correct source, **wrong endpoint** — its v3 measurements API returns empty for history that exists |
| ERA5 via Copernicus CDS                    | ❌ Unnecessary. Open-Meteo Archive **is** ERA5, free, keyless                                         |
| NASA FIRMS gives historical fires          | ⚠️ Only via `*_SP` sources. The `*_NRT` sources return **0 rows** for any historical date             |

Had we built to the original spec, three of the four ingestion modules would have run
without error and produced empty tables.

**The governing principle for this phase: a source is not "working" until it has returned
the specific data a milestone needs. Metadata claiming coverage is not coverage.**

---

## 2. The locked architecture

| Need                        | Source                             | Auth                 | Verified                            |
| --------------------------- | ---------------------------------- | -------------------- | ----------------------------------- |
| **Live** readings           | data.gov.in CPCB resource          | `DATA_GOV_API_KEY`   | ✅ 44 Delhi stations × 7 pollutants |
| **Historical** readings     | **OpenAQ S3 archive**              | **none**             | ✅ 2015–2026, gap 2023–24           |
| Station / sensor metadata   | OpenAQ v3 API                      | `OPENAQ_API_KEY`     | ✅ 96 Delhi locations               |
| Weather + boundary layer    | **Open-Meteo Archive**             | **none**             | ✅ hourly, back to 1940             |
| Fire — historical           | FIRMS `VIIRS_SNPP_SP` / `MODIS_SP` | `NASA_FIRMS_API_KEY` | ✅ 1,604 detections on 2019-10-27   |
| Fire — recent               | FIRMS `VIIRS_SNPP_NRT`             | `NASA_FIRMS_API_KEY` | ✅ available from 2026-04-28        |
| Wards / spatial             | Ward GeoJSON + OSM                 | none                 | ⬜ not yet tested                   |
| Satellite NO₂/SO₂           | Sentinel-5P TROPOMI                | Copernicus OAuth     | ⬜ metadata only, later             |
| Source apportionment priors | NCAP / PRANA report                | none                 | ⬜ not yet tested                   |

### 2.1 Live: data.gov.in ✅

Resource `3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69`, "Real time Air Quality Index".

- **All 3,500 national records share a single `last_update` timestamp.** It is one snapshot
  of the whole country, replaced hourly. There is no archive and no date filter —
  `filters[date]=01-01-2024` returns 0 rows.
- Delhi: **44 stations**, each reporting PM2.5, PM10, NO₂, SO₂, CO, OZONE, NH₃ (308 rows).
- Values are `min_value` / `max_value` / `avg_value` per pollutant, not raw time series.
- **Reliability:** intermittent TLS handshake timeouts observed. Retries are mandatory.

**Role:** the present tense only. Polling it accumulates history at one hour per hour,
which is useless on a sprint timescale. It is not a substitute for the archive.

### 2.2 Historical: the OpenAQ S3 archive ✅

`https://openaq-data-archive.s3.amazonaws.com` — public, unauthenticated, complete.

```
records/csv.gz/locationid={id}/year={yyyy}/month={mm}/location-{id}-{yyyymmdd}.csv.gz
```

List with `?list-type=2&prefix=...`; the response is S3 XML
(namespace `http://s3.amazonaws.com/doc/2006-03-01/`).

CSV columns:

```
location_id, sensors_id, location, datetime, lat, lon, parameter, units, value
```

**Verified Delhi coverage** — stations with data present, per year, across all 96 locations
within 25 km of (28.6139, 77.2090):

| 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023  | 2024  | 2025 | 2026 |
| ---- | ---- | ---- | ---- | ---- | ---- | ---- | ---- | ----- | ----- | ---- | ---- |
| 7    | 11   | 10   | 66   | 46   | 51   | 51   | 50   | **1** | **2** | 55   | 63   |

**The only real gap is 2023–2024.** See §5 for what that costs us.

### 2.3 Why NOT the OpenAQ v3 measurements API — the most important finding ⚠️

**`/v3/sensors/{id}/measurements` returns `0 results` for windows whose data provably
exists in S3.** Verified: 12 sensors whose own metadata claims to span Nov 2019 each
returned zero measurements; the same dates are present as S3 files.

Three v3 endpoints disagree with each other:

| Endpoint                      | Says about Delhi 2019     | True?                                              |
| ----------------------------- | ------------------------- | -------------------------------------------------- |
| `/sensors/{id}/years`         | 83,975 points, 9 sensors  | phantom                                            |
| location `datetimeFirst/Last` | 12 sensors span Nov 2019  | misleading (spans **all** sensors at the location) |
| `/sensors/{id}/measurements`  | 0 results                 | contradicts S3                                     |
| **S3 archive**                | **46 stations have 2019** | ✅ authoritative                                   |

Two traps that cost us time and will cost the next reader more:

1. **A location has multiple sensors per pollutant, across vintages.** Anand Vihar
   (location 235) has PM2.5 sensor `384` covering 2016–2018 _and_ sensor `12235610`
   covering 2025–2026. Taking the first match silently selects a dead sensor.
2. **A location's `datetimeFirst`/`datetimeLast` spans all its sensors**, so location 235
   advertises 2016 → 2026 while having **no data at all between 2019 and 2024.**

**Rule: use v3 for discovery of locations and sensors. Use S3 for every measurement.**

### 2.4 Weather: Open-Meteo Archive ✅

`https://archive-api.open-meteo.com/v1/archive` — free, keyless, and it _is_ ERA5
reanalysis. Verified returning `boundary_layer_height`, `wind_speed_10m`,
`wind_direction_10m`, `temperature_2m` at hourly resolution for November 2019.

**This deletes the Copernicus CDS dependency entirely** — no second account, no job queue,
no GRIB parsing, no multi-hour request latency. That was the largest schedule risk in the
original spec and it is now gone.

Additionally, **OpenAQ carries station-level `wind_speed` and `wind_direction` at ~46 Delhi
sites.** For dispersion reasoning these are preferable to a ~25 km reanalysis cell, because
they measure the actual air that reached the actual monitor. Reanalysis remains the
fallback where a station has no anemometer.

### 2.5 Fire: FIRMS, and the SP/NRT boundary ✅

Verified availability windows (from `/api/data_availability/csv/{key}/all`):

| Source            | From       | To         | Use                 |
| ----------------- | ---------- | ---------- | ------------------- |
| `MODIS_SP`        | 2000-11-01 | 2026-04-30 | deep history        |
| `VIIRS_SNPP_SP`   | 2012-01-20 | 2026-04-27 | **primary history** |
| `VIIRS_NOAA20_SP` | 2018-04-01 | 2026-04-30 | supplementary       |
| `VIIRS_SNPP_NRT`  | 2026-04-28 | 2026-07-10 | recent only         |
| `MODIS_NRT`       | 2026-05-01 | 2026-07-17 | recent only         |

**The `*_NRT` sources return 0 rows for any historical date.** Selecting a source by name
without checking its window is how the original spec would have produced zero fires for
every natural experiment.

**Ingestion rule:** pick the source by the requested date — `*_SP` on or before its
`max_date`, `*_NRT` after. Never hardcode one source.

Quota: **5,000 transactions / 10 minutes**; a multi-day request may count as several.

### 2.6 Not yet touched

Wards/OSM, TROPOMI, and NCAP/PRANA are unverified. They are **not** on the Diwali 2019
critical path except ward boundaries, which are needed for the ward-aggregation step. TROPOMI
stays metadata-only this phase, per the original constraint.

---

## 3. What we are deliberately NOT building

No scheduler. No Redis. No background workers. No cron.

**Automation before correctness is wasted effort.** The deliverable is a script:

```bash
python download_data.py
```

If `download → validate → store → query` is correct once, by hand, it is worth automating.
Until then, a scheduler only makes wrong data arrive on time. Redis has a config slot
(`REDIS_URL`) and stays unconnected.

---

## 4. The gate: reconstruct Diwali 2019 end-to-end

The previous gate ("do we have enough historical data?") is answered: **yes**. The gate is
now:

> **Can the pipeline reconstruct one known natural experiment, end to end?**

**Diwali 2019 — 27 October 2019.** Verified available:

- ✅ **44 Delhi stations** have the `20191027` file in S3
- ✅ **1,604 VIIRS + 103 MODIS** fire detections that day across the stubble belt (74,28→78,31)
- ✅ Open-Meteo returns wind and boundary-layer height for the window

### Why Diwali 2019 is the right choice — and the honest problem with it

Diwali 2019 fell **during peak stubble-burning season**. 1,604 fires burned in Punjab and
Haryana on the day itself. The PM2.5 spike is therefore **confounded**: fireworks and
stubble smoke arrive together.

That is not a reason to pick an easier event. It is the reason to pick this one. A
municipal officer's real question — _"is tonight's spike fireworks or Punjab?"_ — is exactly
this confound. If the pipeline cannot separate them, we learn that now rather than in
Phase 3. **The event is a test of the product's core claim, not just of the plumbing.**

### Implementation order

```
Delhi → one station → one pollutant → one event → one day
      → pipeline complete → scale outward
```

Concretely: **Burari Crossing (location 5541), PM2.5, 27 Oct 2019** — verified to hold 300
rows across 5 pollutants. Prove the whole vertical, then widen.

---

## 5. Scientific risks and limitations

Ordered by how much they threaten the project.

1. **The 2023–2024 hole.** One station in 2023, two in 2024. Any analysis spanning those
   years is not defensible. Historical analogues must be drawn from 2015–2022 or 2025–2026,
   and the discontinuity must be stated wherever a trend is drawn across it.

2. **Diwali is confounded with stubble burning, every year.** Diwali migrates through
   October–November on the lunar calendar — exactly the stubble window. Any Diwali
   attribution that ignores fire counts is wrong. This is the central scientific challenge
   of the project, not an edge case.

3. **Irregular sampling, not hourly.** Real observed timestamps: 00:15, 00:30, 01:00,
   01:30, 02:00, 02:15, 02:45 — gaps are the norm. A validator that expects a reading every
   hour will report every station as broken. Resample explicitly and record the true
   observation count behind every aggregate.

4. **Timezone.** S3 timestamps are **IST (+05:30)**, and the `20191027` file runs to
   `2019-10-28T00:00+05:30`. Diwali's firework peak is at night IST. Treating these as UTC
   shifts the spike by 5.5 hours and attributes it to the wrong day. Store UTC, but reason
   and present in IST.

5. **Station density is uneven and changes over time.** 7 stations in 2015, 66 in 2018,
   46 in 2019. A city-wide mean is not comparable across years, because the stations
   composing it differ. Compare like with like, or state the composition.

6. **Nothing gives us ground truth for source attribution.** FIRMS detects fires, not the
   PM2.5 they delivered to a given ward. Attribution will be _inference under stated
   assumptions_, never measurement. Every claim must carry its evidence and its uncertainty.
   NCAP/PRANA offers published apportionment percentages to sanity-check against — that is a
   comparison, not a validation.

7. **Satellite retrieval quality degrades in exactly the conditions we care about.**
   TROPOMI NO₂ needs `qa_value > 0.75`; Delhi's winter haze and cloud suppress retrievals
   during peak pollution. Expect the satellite to go blind when the story matters. Untested.

8. **data.gov.in returns aggregates, not raw readings** (`min`/`max`/`avg`), while S3 gives
   raw values. Live and historical are therefore **not the same measurement**. Do not draw a
   single line across the join without saying so.

---

## 6. Storage

- **Time-series** (measurements, weather, fires) → PostgreSQL, with PostGIS geometry on
  anything located.
- **Spatial** (wards, OSM polygons) → PostGIS.
- **Raw downloads** → `data/raw/`, **immutable**. Never overwritten, never edited. Every
  processed artefact must be reproducible from `data/raw/` alone.
- **Derived** → `data/processed/`. Disposable by definition; if it cannot be rebuilt from
  raw, it is not derived, it is precious, and it is in the wrong directory.

Database: Supabase PostgreSQL 17.6, **ap-south-1 (Mumbai)**, reached via the Supavisor
pooler (~50 ms round trip). The direct host is IPv6-only and unreachable from Render — see
[deployment.md](deployment.md).

---

## 7. Definition of done

This phase is complete when each question has an evidence-backed answer:

- [ ] Do we have sufficient Delhi station coverage? → station coverage report
- [ ] Which pollutants are reliably available? → per-pollutant uptime
- [ ] Which datasets are trustworthy, and which are too noisy? → validation report
- [ ] Can we scientifically defend the planned attribution pipeline? → limitations doc
- [ ] Do we have enough historical natural experiments? → natural experiment table
- [ ] What are the largest scientific risks? → §5, kept current
- [ ] **Can we reconstruct Diwali 2019 end-to-end?** → the gate

Deliverables: station coverage report · natural experiment table · complete Diwali 2019
pipeline output (raw → validated storage) · scientific limitations document.
