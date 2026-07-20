# Judge FAQ

Answers match the implementation. Where a claim has a primary source in the repository, it is
linked.

---

## Why didn't you use an LLM for decision-making?

Because a recommendation an officer may have to defend in a regulatory meeting has to be
reproducible, and an LLM's is not.

The Decision Engine is deterministic: the same evidence produces the same recommendation,
every time, with a trace from advice back to observation. That property is what makes the
**Challenge Recommendation** feature possible at all. You cannot audit a recommendation you
cannot reproduce.

There is a second reason. An LLM would be fluent about source attribution — and fluency is
exactly the failure mode this project is built to avoid. The hard part here is _not_ producing
plausible-sounding explanations. It is refusing to produce them when the evidence is absent.

## Why didn't you build a source classifier?

**We built one. It scored 98.6% accuracy. We deleted it.**

The specification called for a supervised classifier predicting pollution source. No labels
exist — Delhi's network measures mass concentration, not composition — so the only available
labels were ones we invented from a rule over our own features (e.g. _"high NO₂, low SO₂,
morning peak, low fire influence → Vehicle"_).

That is a rule `y = g(x)`. Training `f(x) ≈ g(x)` learns `g`, not the atmosphere.

We tested this rather than assuming it. Over 13,685 real Delhi station-hours, a random forest
trained on the rule's own inputs scored:

```
5-fold CV:  accuracy 0.9859 ± 0.0035    macro F1 0.9851 ± 0.0038
```

**98.6% accuracy that measures nothing but a random forest's ability to re-learn an
if-statement.**

The danger is not that this fails. It is that it _succeeds_, spectacularly, and every
instrument specified for honesty becomes camouflage:

| Instrument                | What it would report              | What it would mean                  |
| ------------------------- | --------------------------------- | ----------------------------------- |
| Accuracy / F1 / confusion | ~0.99, clean diagonal             | Rule-reproduction fidelity          |
| SHAP                      | "NO₂ dominates the Vehicle class" | NO₂ is in the rule                  |
| Conformal prediction      | 90% coverage, tight sets          | Calibrated coverage **of the rule** |
| Reliability diagram       | On the diagonal                   | The rule is self-consistent         |

Conformal prediction guarantees coverage of `y`. If `y` is fiction, it guarantees coverage of
fiction — rigorously. Statistical machinery cannot manufacture the ground truth it requires as
input.

A second, independent reason: the natural experiments that could anchor labels number about
five or six. No three-class classifier is estimable at n ≈ 6.

Full argument: [`docs/research/inference.md`](../docs/research/inference.md).

## Is this source apportionment?

**No, and the distinction is the point.**

|              | Source apportionment                                              | Source contribution screening _(this)_            |
| ------------ | ----------------------------------------------------------------- | ------------------------------------------------- |
| Output       | "Biomass contributed 62 µg/m³"                                    | "Evidence for the biomass hypothesis is moderate" |
| Requires     | Chemical speciation, receptor modelling (CMB/PMF), tracer species | Routine monitoring + exogenous observations       |
| Ground truth | Measured composition                                              | **None available**                                |
| Claim        | Quantitative attribution                                          | Ranked plausibility of competing explanations     |

Real apportionment needs filter-based speciation and receptor modelling. Delhi's regulatory
network provides neither. Any percentage this system emitted would be invented, so it emits
none — no pie charts, no stacked bars, no contribution figures anywhere in the UI.

## How do you validate the system?

Against **natural experiments** — real interventions that changed one input while leaving
others in place. A module that fails its test is removed, not reinterpreted.

- **COVID lockdown, Mar–Apr 2020** (47 stations, 901,160 rows). Traffic went to ~0 by
  government order, making `P(NO₂ | vehicles ≈ 0)` directly observable rather than assumed.
  Measured: NO₂ −54.4%, SO₂ −3.7%. The NO₂/SO₂ ratio moved 2.82 → 1.34 — a likelihood ratio of
  **2.11**, "weak" on the Kass & Raftery scale. Power generation stayed essential, so SO₂ held
  while NO₂ halved: the differential the hypothesis required. **ACCEPTED.**

  This test could have failed. Had NO₂ not fallen relative to SO₂, the traffic module would
  have been deleted.

- **Diwali 2019.** Tests discriminant validity: can the fire module absorb fireworks and
  misreport them as biomass? 1,604 VIIRS detections were present that day, so the confound is
  real. The structural argument is that VIIRS overpasses Delhi at 12:00–14:00 and 01:00–03:00
  IST, outside the 20:00–00:00 firework window, so the module should not be able to see
  fireworks at all. **PENDING** — that is an argument from the satellite's orbit, not a result.
  The test has not been run, and the engine reports it as pending.

- **Odd-Even II, Apr 2016** (11 stations). The only unconfounded vehicle window — no stubble,
  no winter inversion. Weak treatment on few stations, so it is marked **PENDING** in the UI
  rather than claimed as a pass.

## Why are recommendations deterministic?

Three reasons, in order of importance:

1. **Auditability.** Challenge Recommendation shows evidence → rule → policy →
   recommendation. That trace only means something if the path is reproducible.
2. **Accountability.** An officer acting on this advice owns the consequences. "The model
   suggested it" is not a defence in a review meeting; "rule FIRE_002 fired because upwind
   fire evidence was moderate" is.
3. **Falsifiability.** A deterministic rule can be shown to be wrong. That is a feature.

## Why can the system say "insufficient evidence"?

Because the alternative is worse.

A system that always answers will, on the many hours when the required observations are
missing, produce an answer indistinguishable from one grounded in evidence. An officer cannot
tell the two apart. That is not a gap in the UI — it is a system that quietly lies at a known
rate.

So "insufficient evidence" is a designed output with its own visual treatment, and the UI is
explicit about what it does and does not mean:

> Required observations are unavailable for this window, so no conclusion is drawn. **This is
> not evidence that the source is absent.**

The COVID scenario in the demo is there specifically to show this state. Fires and weather
were never ingested for that window, so the biomass hypothesis cannot be judged — and the
system refuses to guess.

## How do you distinguish Diwali fireworks from agricultural burning?

**Partly, and we are explicit about where the line is.**

The fire module is driven by VIIRS satellite detections of _upwind_ fires 150–250 km away in
the Punjab/Haryana stubble belt. Fireworks in Delhi are neither upwind nor detectable by VIIRS
at that scale, and the satellite's overpasses of Delhi (12:00–14:00 and 01:00–03:00 IST) fall
outside the 20:00–00:00 firework window entirely.

That is a structural argument from the instrument's orbit and resolution, **not a result we
have measured**. The discriminant test that would confirm it is declared with its failure
condition and reported as pending by the engine (§ _How do you validate_).

What we **cannot** do is separate the two contributions to the observed concentration. On
Diwali night in stubble season both are genuinely present, and the episode is permanently
confounded — it recurs every year with the same co-occurrence, so no amount of additional data
resolves it. The system therefore addresses both hypotheses and separates neither, which is
why the Diwali scenario shows fire evidence _and_ traffic evidence without ranking one as the
cause.

See [`docs/research/scientific-limitations.md`](../docs/research/scientific-limitations.md) §2.

## Why does VIIRS sometimes show no fires?

Because a satellite is not a camera pointed at Punjab. It passes overhead roughly twice a day
— for Delhi, near 12:00–14:00 and 01:00–03:00 IST.

So "no detections in the last three hours" is ambiguous between two very different states:

- **an observation gap** — no overpass occurred, so nothing could have been seen; and
- **a true non-detection** — an overpass occurred and found nothing.

The system distinguishes these. An observation gap is reported as missing evidence, never as
evidence of absence. This appears in the Challenge modal as an explicit assumption:

> Satellite overpasses are periodic. An absence of detections in the last hours may be an
> absence of overpass, not an absence of fire.

Cloud cover compounds it: heavy winter haze suppresses detection exactly when the question
matters most. That is listed as a limitation, not worked around.

## Why are you using historical events instead of live data?

Because live data cannot validate a reasoning system. You see the recommendation, and you
never find out whether it was right.

Historical episodes with a known intervention are the only setting where the system's logic
can be tested against something. COVID stopped traffic by decree — that is an experiment
nobody could run deliberately, and it is what made the traffic hypothesis falsifiable.

The console is explicit that these are reconstructions: a **Historical replay** banner on
every screen, "Incident situation" rather than "current", "observed PM2.5" rather than
"current PM2.5".

## Can this run live?

The data layer supports it — the ingestion pipeline is source-agnostic and the same
`/evidence/evaluate` and `/decision/evaluate` endpoints serve any station-hour, historical or
current.

Two honest caveats:

1. Running live would add no validation value, which is why it was not prioritised.
2. Live and archived readings are **not the same measurement** — the live feed is provisional
   and later revised. Mixing them silently would corrupt any comparison. See
   [`scientific-limitations.md`](../docs/research/scientific-limitations.md) §3.4.

## Why Delhi?

It is the hardest available case, and the best instrumented: 96 monitoring stations in the
archive, a documented stubble-burning transport corridor, and — critically — **several real
policy interventions** (Odd-Even I/II/III, the COVID lockdown, GRAP) that function as natural
experiments.

A city with cleaner air and fewer interventions would have made a prettier demo and a weaker
validation story.

## How would this scale to other cities?

The architecture ports; the calibration does not.

- **Ports directly:** ingestion, validation, the Evidence Engine's module interface, the
  Decision Engine, the entire console.
- **Must be redone per city:** the likelihood ratios. Every one is measured against a local
  natural experiment. Reusing Delhi's LR 2.11 in Mumbai would be exactly the kind of
  unearned transfer this project refuses.

So scaling means finding each city's natural experiments and re-running the calibration — a
data problem, not a code problem. Honest, but not a config change, and we would rather say so.

## What are the biggest scientific limitations?

Ranked by how much they should worry you:

1. **No ground truth for attribution exists.** Nothing here is validated against measured
   aerosol composition, because none is collected. This is why the system screens rather than
   apportions.
2. **Diwali and stubble burning are permanently confounded.** They co-occur annually; no
   additional data resolves it.
3. **Traffic is weakly identified.** LR 2.11 is "weak", it is an _upper bound_ (lockdown also
   halted construction and industry), and the module is capped at MODERATE in code as a
   result.
4. **Industry is very weakly identified.** No natural experiment isolates it, so the module
   carries no likelihood ratio at all, and SO₂ reaches only 36 of 96 stations.
5. **The influence kernel is a modelling choice**, not a calibrated physical model. Exponential
   distance decay, cosine upwind alignment, 24-hour linear recency — results are sensitive to
   it, and the Challenge modal says so.
6. **Single-station wind is assumed representative of a 200 km transport path.** In reality
   wind veers with height and distance.

Full list: [`known-limitations.md`](known-limitations.md) and
[`docs/research/scientific-limitations.md`](../docs/research/scientific-limitations.md).
