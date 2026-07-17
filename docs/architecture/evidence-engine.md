# Evidence Engine

> Produces evidence for competing hypotheses. It does not classify pollution sources, does
> not output probabilities, and does not normalise.

Implemented in `apps/api/app/evidence/`. The scientific reasoning behind every constraint
here lives in [../research/inference.md](../research/inference.md).

---

## 1. Why this is not a classifier

Phase 2 tried to build the obvious thing — a supervised model predicting the dominant
source — and stopped. Every metric that design needed (accuracy, F1, confusion matrix,
conformal coverage) requires a **label**: a known dominant source per station-hour,
obtained independently of the features. Measuring one needs receptor modelling, a chemical
transport model, or isotopic tracers. We have none. CPCB and OpenAQ give mass
concentration, and a µg/m³ figure carries no information about origin.

So the only labels available are rules over our own features, which makes the model
circular. **Tested, not assumed:** labels generated from a NO₂/SO₂ and hour-of-day rule,
then learned from the rule's own inputs over 13,685 real Delhi station-hours, scored
**accuracy 0.9859, macro F1 0.9851**. That number measures a random forest re-learning an
if-statement.

The danger is that it _succeeds_. SHAP would report NO₂ as the top feature (it is in the
rule); conformal prediction would deliver calibrated 90% coverage of the rule. Every
instrument meant for honesty becomes camouflage. **Statistical machinery cannot
manufacture the ground truth it takes as input.**

---

## 2. What evidence means here

Evidence for hypothesis `H` from observation `E` is the **likelihood ratio**:

```
LR(H | E) = P(E | H) / P(E | ¬H)
```

Three properties this design needs:

1. **LRs do not sum to 1.** They are not a posterior. A softmax anywhere in this package
   reintroduces source apportionment through the back door.
2. **They map to a published scale** (Kass & Raftery 1995), so a star rating carries a
   citation rather than a taste: 1–3 weak ★, 3–10 substantial ★★, 10–30 strong ★★★,
   30–100 very strong ★★★★, >100 decisive ★★★★★.
3. **They are estimable only where `P(E | H)` is observable** — which is what natural
   experiments provide (§4).

---

## 3. Architecture

```
EvidenceContext        plain dataclass — no session, so modules are pure
      ↓
  ┌── Biomass Module ──┐
  ├── Traffic Module   ┤   each independently testable and replaceable
  └── Industrial ──────┘
      ↓
  Evidence Aggregator      runs all modules, assembles the report
      ↓
  EvidenceReport
```

All I/O lives in `services/context_builder.py`. Modules receive a plain
`EvidenceContext` and never a database session, which is why they unit-test with no
network and why the aggregator can be handed stub modules.

Adding a hypothesis means implementing `EvidenceModule` and appending to
`default_modules()`. The aggregator does not change.

---

## 4. Module identification — the asymmetry is the honesty

| Module         | Identification | LR   | Why                                                                                 |
| -------------- | -------------- | ---- | ----------------------------------------------------------------------------------- |
| **biomass**    | strong         | yes  | FIRMS observes fires from orbit, independently of the monitor being explained       |
| **traffic**    | weak           | 2.11 | No signal exogenous to the monitor; calibrated on COVID, capped at MODERATE in code |
| **industrial** | very weak      | none | No experiment isolates industry; SO₂ at 36 of 96 stations                           |

**Biomass** is the only hypothesis with a predictor that does not come from the sensor we
are trying to explain. That asymmetry decides the whole design.

**Traffic** is calibrated against the COVID lockdown, where traffic went to ~0 by
government order — making `P(NO₂ | vehicles ≈ 0)` directly observable. Measured over 47
stations and 901,160 rows:

```
no2    32.7 -> 14.9   -54.4%
so2    11.6 -> 11.2    -3.7%
NO2/SO2 2.82 -> 1.34   LR = 2.11  (weak)
```

Power generation stayed essential, so SO₂ held flat while NO₂ halved — the differential
the hypothesis requires, and a result the test could have failed to produce. The module is
ACCEPTED and rated honestly: strength is capped at MODERATE **in code**, because LR 2.11
gives no basis for more. The LR remains an **upper bound** — lockdown also halted
construction and industry.

**Industrial** carries no likelihood ratio at all, deliberately. No natural experiment
isolates it.

---

## 5. Strength vs quality — two axes, on purpose

`EvidenceStrength` and `EvidenceQuality` are orthogonal. "Strong evidence on poor data" is
a real and important state — many fires but no wind reading — and collapsing the two would
hide exactly the cases an officer most needs flagged.

`INSUFFICIENT_EVIDENCE` is distinct from `VERY_WEAK`: the first means we could not look,
the second that we looked and found little. Report-level `overall_quality` is the **worst**
judged module, not the mean: a report is only as trustworthy as its weakest component.

---

## 6. Known limitations

1. **A detection gap looks like absence.** Verified: 31 Oct 2019 logged 4 fire detections
   between neighbours of 2,600 and 2,612 — the satellite blinked, the fires did not stop.
   The biomass module currently reports `fires_queried=True, fires=[]` as evidence
   _against_ biomass, which is wrong on such days. The Decision Engine contains this by
   never reasoning from absence, but the module itself should distinguish "looked and saw
   nothing" from "no overpass". **Open.**
2. **The influence kernel is a choice.** Exponential decay halving every 150 km, cosine
   upwind alignment, 24h linear recency. Sensitivity analysis is owed.
3. **Biomass discriminant validity is PENDING.** Tested informally and passed — VIIRS
   overpasses Delhi at 12:00–14:00 and 01:00–03:00 IST, with **zero** detections in the
   20:00–00:00 firework window, so it cannot absorb the firework signal. Not yet a
   committed test.
4. **Odd-Even II is not ingested**, so the unconfounded traffic cross-check has not run.
5. **Road density, industrial and power-plant proximity are not ingested.**

---

## 7. Extension points

- **A new hypothesis:** implement `EvidenceModule`, append to `default_modules()`.
- **A new observation source:** extend `EvidenceContext` and `ContextBuilder`.
- **A new calibration:** add a window to `download_data.py`'s `EVENTS`, run
  `scripts/stress_test.py`, and update the module's constants from the measurement.

Before adding a module, answer: **is there a signal for this hypothesis that does not come
from the sensor we are trying to explain?** If not, it will be weakly identified at best,
and it must say so.
