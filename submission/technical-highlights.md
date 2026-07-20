# Technical highlights

The findings and decisions worth a reviewer's time. Every item here is verifiable in the
repository.

---

## Data engineering

### OpenAQ's live API and its S3 archive disagree about coverage

The live API advertises Delhi stations it will not actually return history for. Building
coverage assumptions on the API would have silently produced a much smaller usable dataset
than expected, discovered late.

Coverage was therefore probed against **S3 directly** — the only source whose claimed coverage
matches what it returns. Result: 96 locations within 25 km of Delhi centre, all with archive
data, 48 with a gap in their year range.

→ [`docs/research/station_inventory/coverage.md`](../docs/research/station_inventory/coverage.md)

### CPCB emits missing-data sentinels as if they were readings

`-999` is the classic one; values near `-476300` were observed in CO. A concentration cannot
be negative, so any negative value is either a sentinel or an instrument fault, and neither
belongs in a mean.

These are dropped **at parse time**, not filtered in queries:

```python
SENTINEL_VALUES = frozenset({-999.0, -9999.0})
...
if numeric < 0 or numeric in SENTINEL_VALUES:
    continue
```

The reason is operational, and learned the hard way: a sentinel that reaches the database is a
sentinel some future query will forget to exclude. An earlier phase stored five of these in
PM2.5 and they had to be excluded by hand at every call site afterwards.

`0` is explicitly _not_ a sentinel — it is a real reading, and there is a test asserting so.

### One physical station appears under several OpenAQ location ids

Naive station counts overstate the network and double-count readings into city means.
Deduplication happens at ingest.

### The 2023–2024 archive gap is real

One station in 2023, two in 2024 — against 50+ in adjacent years. This is not a data-loading
bug; the archive genuinely lacks it.

The console surfaces it as a card in the historical validation timeline rather than
interpolating across it. Showing a gap is a feature; smoothing one is a lie.

### VIIRS overpass timing is a hard constraint

The satellite passes over Delhi roughly twice a day (12:00–14:00 and 01:00–03:00 IST). This
means "no fire detections" is ambiguous between an **observation gap** and a **true
non-detection**, and the two must never be collapsed.

This turned out to be load-bearing in an unexpected way: it is _why_ the fire module cannot
absorb Diwali fireworks. Zero VIIRS detections exist in the 20:00–00:00 firework window,
making the discriminant validity structural rather than tuned.

---

## Inference design

### A self-labelled classifier scored 98.6% and was deleted

Over 13,685 real Delhi station-hours, labels invented from a NO₂/SO₂ and hour-of-day rule, a
random forest trained on the rule's own inputs achieved 5-fold CV accuracy **0.9859 ± 0.0035**
and macro F1 **0.9851 ± 0.0038**.

It had learned the if-statement. The result is in the repository as evidence for a negative
decision, which is the only reason to keep a rejected experiment.

→ [`docs/research/inference.md`](../docs/research/inference.md) §3

### Calibration constants are measured, and enforce their own ceiling

```python
COVID_NO2_NORMAL = 32.7
COVID_NO2_SUPPRESSED = 14.9
COVID_SO2_NORMAL = 11.6
COVID_SO2_SUPPRESSED = 11.2

COVID_LIKELIHOOD_RATIO = RATIO_NORMAL / RATIO_SUPPRESSED  # ~2.11
```

The traffic module is capped at MODERATE strength regardless of what the observations show,
_because_ the measured LR is 2.11 ("weak"). The cap is the measurement, enforced in code
rather than remembered in a document.

A preliminary 3-station run gave −51.5% / −6.6% and LR 1.93; the finding replicated at 15×
the sample. Both numbers are recorded — the superseded one as provenance.

### Modules report the absence of a likelihood ratio rather than borrowing one

No natural experiment isolates industry, so the industrial module carries **no likelihood
ratio at all** and renders:

> No likelihood ratio: no natural experiment isolates this hypothesis, so there is nothing to
> calibrate against.

---

## Frontend

### The theme has no light mode, so `dark:` utilities were a latent bug

The palette is defined once on `:root` in `globals.css`. Tailwind v4's default `dark:` variant
resolves against `prefers-color-scheme`, **not** against the app's theme — so on a laptop set
to light OS mode, every `dark:`-paired utility fell back to its light value and rendered pale
pastel chips and near-white callouts on a pure-black console.

This was invisible on a developer machine in dark mode and would have appeared on a judge's.
All `dark:` usage was removed in favour of the fixed operations palette.

### The visualisation is hand-built SVG, on purpose

No MapLibre, no deck.gl, no tile server, no API key, no SSR workaround. A basemap would be
decoration; what carries the reasoning is the geometry — wind arriving from 315°, fires
sitting upwind 200 km away.

Fires are drawn as an **aggregate in the upwind sector at a representative transport
distance**, not at true coordinates, because the module reasons over aggregate influence and
plotting individual pixels would imply a precision it does not use. The footer says so.

### Queries are self-contained rather than chained

Each React Query is keyed on the scenario and fetches independently. A query that reads
another's `.data` fires against stale values the instant the scenario changes — which, in a
live demo, shows the wrong incident's evidence next to the right incident's header.

### The Diwali scenario needs no database

It is served from a fixed context in the API, so the primary demo path survives a cold Render
instance and a bare checkout. The other scenarios hit live engines against ingested data.

---

## Reliability

### The API refuses to boot with a blank `CORS_ORIGINS`

An empty value disabled the CORS middleware entirely. The symptom was maximally confusing:
`/health` kept returning 200 to curl while every browser request was blocked and the console
rendered blank. The service now fails at boot so Render surfaces it at deploy time instead.

### 68 E2E tests, API mocked at the network boundary

The suite passes on a laptop with no database and on CI with no secrets, and never wakes a
sleeping Render instance. A suite that needs live infrastructure is a suite nobody runs, and
an unrun suite protects nothing. `E2E_LIVE_API=1` runs it against a real backend.

Tests run against a **production build**, not `next dev` — dev overlays and Fast Refresh are
not what a judge sees, and a corrupted `.next` dev cache once made the console render a
permanent skeleton while the API returned 200s.

Notable assertions, which encode product claims rather than implementation details:

- the rendered DOM never contains "probability" or "confidence score";
- it always contains "do not sum to 100%";
- it never contains "current situation" or "current pm2.5" — historical data is never
  presented as live;
- the page itself never scrolls at either viewport;
- Escape closes the Challenge dialog and focus moves into it on open;
- an API failure explains both plausible causes rather than blaming one;
- the console never renders a permanent skeleton.

### Screenshots are generated from the running application

`npm run screenshots --workspace apps/web` drives the real product via Playwright into
`docs/assets/screenshots/`. No mockups, and no drift between the README and the build.
