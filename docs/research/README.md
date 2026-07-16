# Research

Domain and data-source notes. Anything here is input to design decisions, not a decision
itself — those live in `docs/architecture/`.

Suggested files as the work lands:

- `data-sources.md` — coverage, cadence, latency, rate limits, and quirks of each feed.
- `aqi-methodology.md` — CPCB's AQI computation and its sub-index breakpoints.
- `source-attribution.md` — the physical reasoning behind attributing pollution to sources.
- `interventions.md` — the intervention catalogue and evidence for each.

## Data sources under consideration

| Source                | Provides                        | Auth                                          | Notes                                                             |
| --------------------- | ------------------------------- | --------------------------------------------- | ----------------------------------------------------------------- |
| CPCB via data.gov.in  | Ground station measurements     | API key                                       | Station coverage and update cadence vary.                         |
| NASA FIRMS            | Active fire / thermal anomalies | Map key                                       | 5000 transactions / 10 min. A 7-day request may count as several. |
| NASA Earthdata        | Satellite products              | Bearer token                                  | Tokens expire and must be regenerated.                            |
| Copernicus Data Space | Sentinel products               | OAuth 2.0 (user/password → short-lived token) | No static API key. Token is exchanged at request time.            |
| Open-Meteo            | Weather                         | None                                          | Weather drives dispersion; treat as required, not optional.       |
