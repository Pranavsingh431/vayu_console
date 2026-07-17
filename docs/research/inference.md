# Inference Design

> **Status: STOP — the specified target is not scientifically defensible.**
>
> Phase 2's instruction was: _"Stop immediately if the labels are not scientifically
> defensible. If any planned prediction cannot be justified from the available data,
> redesign the target rather than forcing a model."_
>
> This document exercises that instruction. §1–§4 show why the specified target fails.
> §5 onward is the redesign. **No model has been trained and none should be until §5 is
> agreed.**

Last updated 2026-07-17.

---

## 1. The specified target, stated precisely

Phase 2 asks for a supervised classifier:

- **Input:** features `x` at a (station, hour) — gas concentrations, meteorology, fire
  activity, spatial context, time.
- **Output:** `ŷ ∈ {Vehicle, Industrial, Biomass}`, the _dominant source_, plus a
  calibrated confidence.
- **Evaluation:** accuracy, balanced accuracy, precision, recall, F1, confusion matrix,
  calibration error, conformal coverage.

Every element of that evaluation requires a **label**: a known dominant source `y` for each
(station, hour), obtained independently of `x`.

**We do not have `y`, and we cannot obtain it.**

---

## 2. Why no label exists

From `scientific-limitations.md` §1, restated formally.

Let `C_v`, `C_i`, `C_b` be the true PM2.5 mass at a monitor contributed by vehicles,
industry and biomass. The label would be `y = argmax(C_v, C_i, C_b)`.

Measuring `C_k` requires one of:

| Method                                   | Requires                                        | Have it? |
| ---------------------------------------- | ----------------------------------------------- | -------- |
| Receptor modelling (PMF / CMB)           | Speciated filter samples: metals, ions, OC/EC   | ❌ No    |
| Chemical transport model (CMAQ/WRF-Chem) | Gridded emissions inventory + 3D met, validated | ❌ No    |
| Isotopic / tracer apportionment          | ¹⁴C, levoglucosan, or similar markers           | ❌ No    |

CPCB and OpenAQ give **mass concentration only**. A µg/m³ figure carries no information
about origin. There is no transformation of our data that recovers `C_k`.

**Therefore `y` is unobservable in this project. Not "hard to get" — unobservable.**

---

## 3. Any label we invent makes the model circular

The only labels we could construct are rules over our own features, e.g. the Phase 2 spec's
own worked example: _"High NO2, Low SO2, morning peak, road density, low fire influence →
Vehicle."_

That is a rule `y = g(x)`. Training `f(x) ≈ y = g(x)` learns `g`, not the atmosphere.

**This was tested, not assumed.** Labels were generated from a NO2/SO2 ratio and hour-of-day
rule, and a random forest was trained on the rule's own inputs, over 13,685 real Delhi
station-hours:

```
labels invented by the rule:
  Vehicle      6,396  (46.7%)
  Industrial   2,539  (18.6%)
  Biomass      4,750  (34.7%)

5-fold CV, features = the rule's own inputs:
  accuracy  0.9859 ± 0.0035
  macro F1  0.9851 ± 0.0038
```

**98.6% accuracy that measures nothing but a random forest's ability to re-learn an
if-statement.**

The danger is not that this fails. It is that it _succeeds_, spectacularly, and every
instrument Phase 2 specified for honesty becomes camouflage:

| Instrument                | What it would report              | What it would mean                  |
| ------------------------- | --------------------------------- | ----------------------------------- |
| Accuracy / F1 / confusion | ~0.99, clean diagonal             | Rule reproduction fidelity          |
| SHAP                      | "NO2 dominates the Vehicle class" | NO2 is in the rule                  |
| Conformal prediction      | 90% coverage, tight sets          | Calibrated coverage **of the rule** |
| Reliability diagram       | On the diagonal                   | The rule is self-consistent         |

Conformal prediction guarantees coverage of `y`. If `y` is fiction, it guarantees coverage
of fiction — rigorously. **Statistical machinery cannot manufacture the ground truth it
requires as input.** Applying it here would make the fabrication harder to detect, not
easier.

---

## 4. Natural experiments cannot rescue the label either

The obvious reply: use the natural experiments as labels. COVID lockdown ⇒ vehicles ≈ 0.

Three reasons this fails as **training** data:

1. **`n` is events, not hours.** Delhi PM2.5 is strongly autocorrelated hour to hour and
   spatially correlated station to station. The 186,977 rows from the Diwali window are not
   186,977 independent draws — they are one meteorological episode observed densely. The
   effective sample size for learning an event-level label is **the number of independent
   interventions: ~5–6**. No 3-class classifier is estimable at n≈6.

2. **The events do not label the target.** COVID tells us vehicle emissions _fell_. It does
   not tell us `argmax(C_v, C_i, C_b)` in any hour. "Less vehicle" is not "industry
   dominant".

3. **Every event is confounded.** Diwali 2019 coincided with 1,604 upwind fires. Odd-Even
   III ran during peak stubble season. COVID's counterfactual is contaminated by an
   unusually wet spring. Confounded events cannot label a variable they cannot isolate.

Natural experiments remain extremely valuable — but as **held-out tests of construct
validity** (§7), not as training labels. n≈6 is fine for that and useless for this.

---

## 5. The redesign: predict what we can observe

The name in the Phase 2 brief was already right — **Source Contribution Screening, not
Source Apportionment**. The machinery specified underneath it (classifier, F1, confusion
matrix) silently reintroduced apportionment. This redesign makes the machinery match the
name.

### 5.1 The asymmetry that decides the design

| Source      | Independent, exogenous signal available?                                                       | Estimable? |
| ----------- | ---------------------------------------------------------------------------------------------- | ---------- |
| **Biomass** | ✅ **Yes** — FIRMS detects fires from orbit, entirely independently of the air-quality monitor | **Yes**    |
| Vehicle     | ❌ No — its only signature is in the same chemistry we would label from                        | No         |
| Industrial  | ❌ No — same problem; SO2 is measured at only 36 of 96 stations                                | No         |

**This asymmetry is the whole design.** Fire is the one source with a predictor that does
not come from the sensor we are trying to explain. That makes fire influence a genuine
statistical estimand and vehicle/industrial share a fiction.

### 5.2 Component A — PM2.5 regression (a real, observed target)

- **Target:** `PM2.5` at (station, hour). **Measured.** Not invented.
- **Features:** meteorology (wind speed/direction, BLH, temperature, RH), wind-weighted
  upwind fire influence, temporal (hour, weekday, month, festival, GRAP stage), spatial
  (road density, industrial proximity), lags and rolling means.
- **Models:** the spec's list is appropriate here — baseline linear, random forest,
  LightGBM, XGBoost.
- **Uncertainty:** **conformal prediction is legitimate here**, because `y` is a real
  measurement. Coverage means what it claims.
- **Explainability:** SHAP over this model is meaningful — it explains a model of an
  observed quantity.

This is defensible because every number in it was measured.

### 5.3 Component B — fire contribution by counterfactual

The one source decomposition our data supports:

```
Δ_fire(t) = E[PM2.5 | fire influence as observed] − E[PM2.5 | fire influence = 0]
```

- **Estimand:** the excess PM2.5 associated with upwind fire activity, in µg/m³, with a
  conformal interval.
- **Why defensible:** the outcome is observed and the treatment (upwind FRP, wind-weighted)
  is exogenous — satellites do not read our monitors.
- **Assumptions, which must be stated with every output:**
  - No unmeasured confounder drives both fire activity and Delhi PM2.5. **This is violated
    in the obvious direction:** stubble burning and Delhi's winter inversion are both
    seasonal. Meteorological adjustment mitigates but does not eliminate it.
  - The wind-weighted influence kernel is a modelling choice, not a measurement.
  - Extrapolating to `fire = 0` is off-support in October–November, when fires are never
    zero.
- **Honest status:** this is an **association under stated assumptions**, presented as such.
  Not "stubble caused X".

### 5.4 Component C — the Evidence Engine

An earlier draft of this document proposed loose "screening indicators". That was too weak.
An indicator reported as `Biomass 0.93` is the same if-statement as §3, wearing decimals.
**A number with two significant figures must have a definition, or it is a heuristic in a
lab coat.**

Evidence already has a formal definition. Evidence for hypothesis `H` from observation `E`
is the **likelihood ratio**:

```
LR(H | E) = P(E | H) / P(E | ¬H)
```

This is what "evidence" means in Bayesian statistics, and what a diagnostician computes. It
has exactly the properties this system needs:

1. **LRs do not sum to 1 across hypotheses.** They are not a posterior. Reporting
   `Vehicle 0.72, Industrial 0.21, Biomass 0.93` is coherent — these are strengths of
   evidence, not shares of a pie. **A softmax anywhere in this system reintroduces
   apportionment through the back door.**
2. **It maps to a published interpretation scale** (Kass & Raftery 1995), so a star rating
   carries a citation rather than a taste:

   | LR     | Interpretation | Stars |
   | ------ | -------------- | ----- |
   | 1–3    | weak           | ★     |
   | 3–10   | substantial    | ★★    |
   | 10–30  | strong         | ★★★   |
   | 30–100 | very strong    | ★★★★  |
   | >100   | decisive       | ★★★★★ |

3. **It is estimable — but only where `P(E | H)` is observable.** That constraint is what
   keeps the engine honest; §5.5 is how we satisfy it.

Each module emits `LR`, supporting observations, **contradictory observations**, its
assumptions, and an **identification status**. It never emits a probability of a source.

### 5.5 Where `P(E | H)` becomes observable: natural experiments as calibration

A natural experiment is a period in which `H` is **known by external fact**. That makes the
conditional distribution directly measurable rather than assumed:

- COVID lockdown ⇒ traffic ≈ 0, by government order. The observed NO₂ distribution in that
  window **is** `P(NO₂ | vehicles ≈ 0)`. Measured, not modelled.
- Normal periods give `P(NO₂ | vehicles normal)`.
- Their ratio is the vehicle module's LR — calibrated against a real intervention.

This is the load-bearing idea of the redesign, and it is what separates a calibrated
evidence score from a tuned one. §4 stands: n≈6 is useless for _training a classifier_. But
each event supplies thousands of station-hours drawn from a **known condition**, which is a
distributional estimate, not a single labelled draw. Different question, different n.

### 5.6 Identification status per module — the asymmetry is the honesty

The three modules do not survive this equally, and the UI must show it:

| Module         | Calibrating experiment           | Status        | Why                                                                   |
| -------------- | -------------------------------- | ------------- | --------------------------------------------------------------------- |
| **Biomass**    | Stubble seasons, FIRMS-confirmed | **Strong**    | Exogenous satellite signal; many seasons; treatment directly observed |
| **Vehicle**    | COVID 2020 + Odd-Even II 2016    | **Weak**      | See below                                                             |
| **Industrial** | COVID (partial)                  | **Very weak** | SO₂ at 36 of 96 stations; no intervention isolates industry           |

**Why vehicle is weak.** COVID did not isolate traffic — it stopped traffic, construction
and much industry simultaneously. `P(NO₂ | vehicles≈0)` estimated from lockdown is really
`P(NO₂ | most activity ≈ 0)`.

One exception makes it testable anyway: **power generation was essential and kept running.**
COVID is therefore a _differential_ intervention — traffic ↓↓, power ~unchanged — which
yields a sharp, discriminating, falsifiable prediction:

> If NO₂ tracks traffic and SO₂ tracks power generation, the **NO₂/SO₂ ratio must collapse
> during lockdown.** If it does not, NO₂ is not a traffic-specific proxy in Delhi, and the
> vehicle module is deleted.

**Odd-Even II (April 2016)** is the only unconfounded vehicle window — outside stubble
season and outside winter inversion. But 11 stations, and the policy exempted two-wheelers
and CNG, i.e. most of Delhi's fleet: a weak treatment on a small panel.

**Both are calibrated, and both are reported, including where they disagree.** Selecting the
flattering experiment and omitting the other would be the same dishonesty as inventing
labels, one level up.

### 5.7 Stress tests are falsification, not validation

Each module must pass tests **written so that they can fail**. Outcome is
`Accepted / Rejected / Uncertain`.

| Test                           | Module  | Rejects the module if…                                      |
| ------------------------------ | ------- | ----------------------------------------------------------- |
| COVID lockdown 2020            | Vehicle | NO₂ does not fall materially when traffic is ~0             |
| COVID NO₂/SO₂ ratio            | Vehicle | The ratio does not collapse (⇒ NO₂ is not traffic-specific) |
| Odd-Even II, Apr 2016          | Vehicle | No detectable NO₂ response in an unconfounded window        |
| Stubble seasons                | Biomass | `Δ_fire` does not track FIRMS counts                        |
| Diwali (discriminant validity) | Biomass | `Δ_fire` absorbs the firework spike                         |

**A rejected module is deleted from the product**, and the failed test is written up in
`scientific-limitations.md`. Falsification needs no minimum n — one decisive test kills a
hypothesis. This is the difference between stress tests that are real and stress tests that
are ceremonial.

The system will then carry fewer hypotheses, and every survivor will have passed a test it
could have failed.

---

## 6. Output contract

**Never:**

```
Vehicle Emissions — 41%
Vehicle Emissions — confidence 0.78
```

**Instead:**

```
PM2.5 at Anand Vihar, 27 Oct 2019 23:30 IST: 1288 µg/m³ (observed)

  Expected without upwind fire influence:  612 µg/m³  [95% CI 480–760]   (conformal)
  Excess associated with fire influence:   676 µg/m³  [95% CI 528–808]
    Evidence: 1,604 VIIRS detections within 300 km upwind in the prior 12 h;
              wind 315° at 4 m/s; boundary layer 210 m (12th percentile for October).
    Assumes: no unmeasured seasonal confounder; influence kernel as documented.
             Fire ≈ 0 is off-support in October — this is an extrapolation.

  Screening indicators (consistency, NOT contribution):
    NO2/SO2 = 8.2  — consistent with mobile/distributed combustion over point sources
    Diurnal profile — does NOT match a traffic profile this hour (peak is 23:30)
    SO2 = 11 µg/m³, below the October median — little sign of point-source influence

  This system does not measure source shares. See scientific-limitations.md §1.
```

Note what the example does: it gives the officer a number where a number is earned
(fire excess, from an exogenous signal), and refuses to give one where it is not
(vehicle share). **The refusal is the product.** A tool that says "41% traffic" when it
cannot know is worse than useless to someone who has to defend the decision.

---

## 7. Validation: natural experiments as construct validity

Not training data (§4). Used as **held-out tests of whether an indicator measures what it
claims**:

| Event                 | External fact                                           | Falsifiable prediction                                                                                                        |
| --------------------- | ------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| COVID lockdown 2020   | Vehicle activity collapsed                              | The NO₂-based indicator must fall sharply. **If it does not, NO₂ is not a vehicle proxy in Delhi and §5.4 row 1 is deleted.** |
| Odd-Even II, Apr 2016 | Partial vehicle reduction, **no stubble, no inversion** | Small NO₂ fall. The only unconfounded vehicle window we have.                                                                 |
| Stubble season        | Fires high, verified by FIRMS                           | `Δ_fire` must be large and track fire counts                                                                                  |
| Diwali                | Firework emissions, **confounded**                      | `Δ_fire` must not absorb the firework spike — a test of _discriminant_ validity                                               |

**Reported as event studies with n≈6, with confidence intervals reflecting that n.** Not as
classifier metrics. There is no confusion matrix because there are no classes.

Each row above is written so it **can fail**. If the COVID test fails, we delete the
indicator rather than reinterpret the result.

---

## 8. What this costs

Honest accounting of what the redesign gives up:

- **No "dominant source" label.** The headline output of the original spec does not exist.
- **No accuracy / F1 / confusion matrix.** Nothing to be accurate against.
- **Vehicle and industrial are never quantified**, only screened.
- **Less impressive.** "98.6% accuracy at identifying pollution sources" is a much better
  demo than "we can bound fire influence and decline to guess the rest."

What it buys: **every number the system emits can be defended.** Under questioning from an
atmospheric scientist, §5 survives and §1–§4 is why. The original design does not survive
the first question, which is _"where did your labels come from?"_

---

## 9. Failure modes of the redesign

1. **Off-support extrapolation.** `fire = 0` never occurs in October–November. The
   counterfactual is an extrapolation there and must be flagged in-band, per prediction.
2. **Seasonal confounding.** Stubble season and inversion season coincide. Meteorological
   adjustment reduces but cannot remove this. `Δ_fire` is biased upward if BLH is
   imperfectly controlled.
3. **The influence kernel is a choice.** Distance-weighted FRP with a wind sector is one
   defensible parameterisation among many; results are sensitive to it. Sensitivity analysis
   is mandatory, not optional.
4. **SO₂ at 36 of 96 stations only.** Industrial screening is unavailable at 60 stations.
   Absence of an indicator must never render as absence of the source.
5. **The 2023–2024 hole** (limitations §3.1) and **location-id fragmentation** (§3.2) both
   bite any multi-year fit. Dedup must land before cross-year training.
6. **Sentinel values.** `-999` appears in stored PM2.5 (5 rows) and CO carries values near
   `-476300`. Ingestion currently stores what the validator flags. **Filtering must precede
   any fit.**

---

## 10. Decision required

This document does not implement a classifier, and the specified one should not be built.

**Recommended:** adopt §5 — regression on observed PM2.5, counterfactual fire influence
with conformal intervals, and unlearned screening indicators for vehicle and industrial.

**The alternative** — build the specified 3-class model on rule-derived labels — produces
~0.99 accuracy, a clean confusion matrix, confident SHAP plots, and calibrated conformal
sets, all of which are artefacts of an if-statement. It would demo well and it would be
fabrication.

If the judging criteria require a "dominant source" output, the defensible version is
**§6's evidence block**, not a class label. That is a product decision, and it should be
made deliberately rather than by a model quietly inventing labels.
