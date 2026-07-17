# Demo Script — 5 minutes

> Open `/console` on a 16:9 screen. Nothing scrolls. Everything below is on one screen.
>
> **If you have 45 seconds, click `Present Incident` and stop reading.** The console
> walks itself through the reasoning. The rest of this is what to say over it.

---

## 0:00 — The situation (15s)

**Point at the top-left number.**

> "This is Anand Vihar, Delhi, on Diwali night 2019. PM2.5 is **1,288 micrograms** —
> twenty times the safe limit. An officer opening this at 11:30pm has one question:
> what do I do about it?"

**Notice:** severity is the measured concentration against CPCB's published breakpoints.
Not a model output. A number an officer can cite.

---

## 0:15 — The problem (30s)

**Point at the map.**

> "The wind is coming from 315 degrees — the north-west. And 28 fire detections sit
> exactly upwind, in Punjab. That's the stubble burning."
>
> "But it's also Diwali. Fireworks. **Two explanations arrive at the same time**, and
> most systems would pick one."

**This is the whole product.** Do not rush it.

---

## 0:45 — The evidence (60s)

**Point at the Evidence panel.**

> "We don't pick. We show the evidence for each explanation independently."
>
> "Fire: moderate. Traffic: very weak. Industry: very weak."

**Click "Fire / Biomass" to expand.**

> "Every one of these is a real observation with a source. And notice the likelihood
> ratio — that's a Bayesian evidence measure, mapped to published bands from Kass and
> Raftery 1995. Not a probability we invented."

**Say this line. It is the differentiator:**

> "These do not add up to 100%. They're not source shares. **This system does not claim
> to measure how much came from where — because with this data, nobody can.**"

---

## 1:45 — The decision (45s)

**Point at Recommended action.**

> "Two recommendations. Issue a public health advisory. Increase monitoring."
>
> "Notice what's **missing**: no traffic enforcement. It's 11:30pm — not a commute
> hour. The engine refuses to recommend rush-hour enforcement at midnight, even though
> NO₂ is elevated."

**Point at the amber Human Review banner.**

> "And it's telling the officer it needs a human, and exactly why."

---

## 2:30 — Challenge (90s) — THE MOMENT

**Click `Why?` on the advisory.**

> "This is what an officer needs when they're challenged in a meeting."

**Walk the trace top to bottom:**

> "Evidence → Rule FIRE_002 → Policy → Recommendation. Four steps from a satellite
> observation to an action."
>
> "The rule states **why it's defensible**, in its own words."
>
> "Supporting evidence. **Contradicting evidence — we show what argues against our own
> recommendation.** Assumptions. Limitations."
>
> "And 'how far this can be pushed' — in prose, not a confidence score. A number there
> would imply precision we don't have."

---

## 4:00 — Why you can trust it (60s)

**Point at the timeline.**

> "Every module was tested against a real intervention, with a test it could have failed."

**Point at COVID (green, CALIBRATED).**

> "COVID lockdown. Traffic stopped by government order. **NO₂ fell 54%. SO₂ fell 4%** —
> power stations stayed running. That differential is the only reason we trust NO₂ as a
> traffic signal at all."
>
> "The measured likelihood ratio was 2.11 — that's 'weak' on the published scale. **So
> we cap the traffic module at moderate. In code.** We could have said strong. The
> measurement said weak."

**Point at Archive gap (red).**

> "And here's a two-year hole in the data. We show it rather than interpolate across it."

---

## Closing line

> "We built a source classifier first. It scored **98.6% accuracy** — and we deleted it,
> because it had learned our own labelling rule. There is no ground truth for source
> attribution in this data. So we built something that argues from evidence instead, and
> tells you when it can't see.
>
> **That's the difference between a demo and a tool someone would actually open at 2am.**"

---

## If a judge asks…

| Question                          | Answer                                                                                                                                                                              |
| --------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| "Why no percentages?"             | Measuring source contribution needs receptor modelling, a chemical transport model, or isotopic tracers. We have none. Any percentage would be fabricated.                          |
| "Why is industry always weak?"    | No natural experiment isolates industry — COVID stopped traffic, construction and industry together. So the module carries no likelihood ratio at all.                              |
| "Is there an LLM?"                | No. The decision engine is deterministic rules. Same evidence, same advice, every time — auditable months later.                                                                    |
| "What's the accuracy?"            | There isn't one, and that's the point. Accuracy requires labels. We have no labels for source attribution, so any accuracy figure would measure agreement with our own assumptions. |
| "Why is COVID greyed with a dot?" | Fires and weather weren't collected for that window, so biomass reports insufficient evidence. The system says "I can't see" instead of guessing.                                   |
| "Where's GRAP?"                   | It's a threshold-triggered regime, not a dated event. There's no single station-hour to reconstruct, so including it would mean inventing one.                                      |

---

## Do not

- Don't scroll. Nothing needs it.
- Don't apologise for weak evidence. **It's the strongest thing here.**
- Don't say "AI" unprompted. Say "evidence" and "reasoning".
