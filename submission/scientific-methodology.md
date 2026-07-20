# Scientific methodology

## The claim this system makes, stated precisely

> Given an observed pollution episode, rank the plausibility of competing explanations using
> evidence that is, where possible, observed independently of the measurement being explained
> — and decline to rank when the required observations are missing.

It does **not** claim to quantify how much any source contributed.

## Source apportionment vs source contribution screening

|                   | Source apportionment                                          | Source contribution screening _(this system)_           |
| ----------------- | ------------------------------------------------------------- | ------------------------------------------------------- |
| Output            | "Biomass contributed 62 µg/m³ (95% CI 48–79)"                 | "Evidence for the biomass hypothesis is moderate"       |
| Method            | Receptor modelling — CMB, PMF — over speciated filter samples | Hypothesis-wise evidence from exogenous observations    |
| Requires          | Chemical speciation, tracer species, source profiles          | Routine regulatory monitoring + satellite + meteorology |
| Ground truth      | Measured composition                                          | **None available**                                      |
| Validated against | Known source profiles                                         | Natural experiments                                     |
| Failure mode      | Wrong numbers                                                 | Wrong ranking, or an honest refusal                     |

Delhi's regulatory network measures **mass concentration, not composition**. Apportionment
requires composition. The instrumentation gap is not something a model can close: no amount of
statistical machinery converts PM2.5 mass into the speciation it was never measured with.

So the choice was between fabricating percentages and changing the question. We changed the
question.

## Why the obvious approach was rejected

The specified approach — a supervised classifier predicting source — has no labels. Delhi has
no labelled dataset of "this station-hour was caused by vehicles" because producing one would
itself require apportionment.

Inventing labels from a rule over our own features makes the model circular. We tested this:
13,685 real station-hours, labels from a NO₂/SO₂ and hour-of-day rule, random forest on the
rule's own inputs → **98.6% accuracy, 98.5% macro F1**. The model learned the if-statement.

The instructive part is that every honesty instrument would have _corroborated_ the
fabrication — SHAP would have attributed importance to the features in the rule, conformal
prediction would have delivered calibrated coverage of the rule, the reliability diagram would
have sat on the diagonal. Statistical rigour applied to a fabricated target produces rigorous
fabrication.

Detail: [`docs/research/inference.md`](../docs/research/inference.md) §§1–4.

## What replaced it: identification, then evidence

The redesign rests on one asymmetry. Some hypotheses have evidence that exists **outside** the
measurement being explained; some do not. That is _identification_, and it is reported
separately from evidence strength, because it does not vary by the hour — it is a property of
what can be observed at all.

| Hypothesis         | Identification | Exogenous signal                                                                | Likelihood ratio                  |
| ------------------ | -------------- | ------------------------------------------------------------------------------- | --------------------------------- |
| **Biomass / fire** | Strong         | FIRMS/VIIRS observes fires from orbit, independently of the air-quality monitor | Kernel-based                      |
| **Traffic**        | Weak           | None. The only signature is in the same chemistry we reason from                | 2.11 (measured, COVID)            |
| **Industrial**     | Very weak      | None, and no natural experiment isolates it                                     | **None** — and the module says so |

A module with no likelihood ratio reports that it has none, rather than borrowing one.

## Where `P(E | H)` becomes observable

The move that makes this more than a heuristic: a natural experiment sets a hypothesis's cause
to a known value by external force, which makes the conditional directly observable rather
than assumed.

COVID set traffic ≈ 0 by government order. That makes `P(NO₂ | vehicles ≈ 0)` measurable:

```
                 pre-lockdown    lockdown     change
  NO₂               32.7           14.9       −54.4%
  SO₂               11.6           11.2        −3.7%
  NO₂/SO₂ ratio      2.82           1.34
```

Likelihood ratio = 2.82 / 1.34 = **2.11** — "weak" on the Kass & Raftery scale.

Three things about that number are worth stating:

1. **It is measured, not chosen.** It lives in code as a constant derived from the ingest, and
   the module is capped at MODERATE strength _because_ of it. The cap is the measurement,
   enforced.
2. **It is an upper bound.** Lockdown also halted construction and industry, so 2.11
   over-credits traffic.
3. **The test could have failed.** Had NO₂ not fallen relative to SO₂, the traffic module
   would have been deleted rather than reinterpreted.

## Stress tests are falsification, not validation

Each natural experiment is framed as an attempt to break a module, with the failure condition
stated before the run:

| Experiment     | Failure condition                                 | Outcome                                                                |
| -------------- | ------------------------------------------------- | ---------------------------------------------------------------------- |
| COVID lockdown | NO₂ does not fall relative to SO₂                 | Survived → **ACCEPTED**                                                |
| Diwali 2019    | Fire module absorbs fireworks as biomass evidence | Survived (zero VIIRS detections in the firework window) → **VERIFIED** |
| Odd-Even II    | —                                                 | Not yet run to conclusion → **PENDING**, and shown as such             |

"PENDING" appears in the UI. A test not yet passed is not quietly presented as a pass.

## What the system may and may not say

**May say:**

- "Evidence for the biomass hypothesis is moderate."
- "Observed wind geometry is consistent with transport from upwind fire activity."
- "Required observations are unavailable; no conclusion is drawn."
- "This recommendation follows from rule FIRE_002 under policy PUBLIC_HEALTH."

**May not say, and does not:**

- "Biomass contributed X µg/m³" or "X% of PM2.5 is vehicular."
- "Fires caused this episode."
- Any probability that a source is responsible.
- Any forecast concentration, or any estimate of an intervention's effect.

The E2E suite asserts the negative cases against the rendered DOM — the words "probability"
and "confidence score" must not appear, and "do not sum to 100%" must.

## Reporting conventions

- **Evidence strength** uses Kass & Raftery likelihood-ratio bands, rendered as five slots.
  The UI states "not a probability" wherever a ratio appears.
- **Evidence quality** describes the observations, not the conclusion, and is reported
  separately.
- **Insufficient evidence** is its own state, visually distinct, with explicit copy that it is
  not evidence of absence.
- **Strengths do not sum to 1**, and the panel says so. The hypotheses are not mutually
  exclusive, which is also why there is no pie chart anywhere in the product — any such chart
  would reintroduce the apportionment the system refuses.
