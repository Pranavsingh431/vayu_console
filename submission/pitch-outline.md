# Pitch outline

Ten slides. Speaker notes are the _argument_, not a script — say them in your own words.

Adjust the count if the hackathon caps it: slides 5 and 6 are the ones that win a technical
room, slides 1 and 8 are the ones that win a mixed one. Slide 9 is the first to cut.

---

## 1 — The problem

> **AQI dashboards tell cities how bad the air is.
> They don't tell cities what action the evidence justifies.**

_Notes._ Delhi has no shortage of air quality dashboards. An officer looking at one during a
severe episode already knows the air is bad — that is why they are at their desk at 2am. What
they have to decide is what to do, and how to defend it tomorrow. No dashboard answers that,
because answering it means reasoning about evidence rather than displaying a number.

Do not linger. The audience already believes this.

---

## 2 — Vayu Console

> **Situation → Evidence → Decision → Explanation**

_Notes._ Four words, and the product is literally laid out in that order. Evidence comes
_before_ decision, structurally: the Decision Engine may only read the Evidence Engine's
output, so no rule can reach a recommendation the evidence does not carry.

---

## 3 — The live product

_Screenshot: `docs/assets/screenshots/02-console-diwali.png`, or switch to the live console._

_Notes._ Diwali 2019, 23:30, Anand Vihar: 1,288 µg/m³. Roughly twenty times the daily
standard.

Say the replay point here, unprompted, before anyone wonders: **everything in this console is
a reconstruction of a real past incident.** Nothing is live, and the console says so on every
screen. Get ahead of it — it reads as rigour when you volunteer it and as evasion when you are
asked.

---

## 4 — The Evidence Engine

_Screenshot: evidence panel._

_Notes._ Three hypotheses — fire/biomass, traffic, industry — each evaluated independently,
each with supporting _and_ contradicting observations.

The line that lands: **these do not add up to 100%, and that is not an oversight.** The
hypotheses are not mutually exclusive. On a Diwali night in stubble season, fire and traffic
evidence are both genuinely present. Any chart implying shares would be a lie about what we
can know.

---

## 5 — Scientific honesty

> **This is source-contribution screening, not source apportionment.**

_Notes._ The slide that separates this from every other entry.

Apportionment needs chemical speciation and receptor modelling. Delhi's network measures mass,
not composition. So any percentage we emitted would be fabricated — and we emit none.

Then the story: we built the obvious thing first. A supervised source classifier. It scored
**98.6% accuracy**. We deleted it, because the labels came from our own rule, so the model had
learned the rule rather than the atmosphere. And every honesty instrument — SHAP, conformal
prediction, calibration curves — would have _corroborated_ it. Statistical rigour applied to a
fabricated target produces rigorous fabrication.

This is the single most memorable thing you will say. Do not rush it.

---

## 6 — Validation

> **Natural experiments. A module that fails its test is removed, not reinterpreted.**

_Notes._ COVID stopped traffic by government decree — an experiment nobody could run
deliberately. That makes `P(NO₂ | vehicles ≈ 0)` observable rather than assumed.

Measured over 47 stations and 901,160 rows: NO₂ −54.4%, SO₂ −3.7%. Power generation stayed
essential, so SO₂ held while NO₂ halved — the differential the hypothesis required.

Likelihood ratio **2.11**. That is "weak", and we report it as weak, and the module is capped
at MODERATE in code because of it.

Emphasise: **the test could have failed.** Had NO₂ not fallen relative to SO₂, we would have
deleted the traffic module.

---

## 7 — The Decision Engine

> **Evidence → Rule → Policy → Recommendation. Deterministic.**

_Notes._ No model between the evidence and the advice. The same evidence produces the same
recommendation every time.

If asked why not an LLM: because a recommendation an officer defends in a regulatory meeting
has to be reproducible, and auditability is impossible without it. Also — fluency is the
failure mode we are avoiding. The hard part is not producing plausible explanations; it is
refusing to produce them when the evidence is absent.

---

## 8 — Challenge Recommendation

_Screenshot: `docs/assets/screenshots/03-challenge-modal.png`. Better: do it live._

_Notes._ One click, and the officer sees the full trace from advice back to observation.
Supporting evidence, **contradicting evidence — never hidden**, assumptions, limitations.

The framing that lands: this is not built to convince the officer the system is right. It is
built so someone can prove it wrong. An officer needs the counter-argument before someone else
in the meeting supplies it.

Then pivot to the COVID scenario: **insufficient evidence.** No recommendation can be
justified. Required observations are missing and the system refuses to guess — and it is
explicit that this is not evidence the air is clean.

---

## 9 — Architecture

_Diagram: the Mermaid system diagram from the [README](../README.md#architecture)._

_Notes._ Keep it to twenty seconds unless asked. OpenAQ S3 + FIRMS + Open-Meteo → validation →
Postgres/PostGIS → Evidence Engine → Decision Engine → FastAPI → Next.js console.

One detail worth naming if the room is technical: the map is hand-built SVG. No tile server,
no API key, nothing that can fail in a demo.

---

## 10 — Impact and scalability

_Notes._ Honest, specific, no invented market numbers.

**What ports:** ingestion, validation, both engines, the entire console.
**What does not:** the calibration. Every likelihood ratio is measured against a local natural
experiment. Reusing Delhi's 2.11 in Mumbai would be exactly the unearned transfer this project
refuses.

So scaling means finding each city's natural experiments — a data problem, not a code problem.
Say that plainly. Claiming one-click multi-city would undercut everything in slide 5.

Close on:

> **Most systems are designed to always give an answer. Vayu Console is designed to give an
> answer only when the evidence can support one — and to show exactly why.**

---

## Do not

- Invent market sizing, user counts, or projected impact figures.
- Say "AI-powered" — the differentiator is that the decision layer is deliberately _not_ a
  model.
- Claim live operation. The console replays historical incidents, on purpose.
- Present "98.6%" as an achievement. It is the cautionary tale, and the pivot depends on the
  audience hearing it that way.
