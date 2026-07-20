# Five-minute demo script

**Setup before you start.** Open the console on the Diwali 2019 scenario, at 1440×900 or
larger. Warm the API first — hit `/health` once so Render is not cold. Have the COVID tab
ready but unclicked.

If anything goes wrong, `Present Incident` runs the whole sequence hands-free in ~35 seconds,
and Escape always exits it.

---

## 0:00–0:30 — The problem

> Delhi has plenty of air quality dashboards. Every one of them tells an officer the same
> thing: how bad the air is right now.
>
> That is not the officer's problem. Their problem is what to _do_ — and how to defend that
> decision in a review meeting the next morning. No dashboard answers that, because answering
> it means reasoning about evidence, not displaying a number.

## 0:30–1:00 — Open the console, explain the replay

Open the Operations Console.

> First thing to notice: this bar at the top. **Historical replay.** Everything in this
> console is a reconstruction of a real past incident from archived observations. Nothing here
> is live.
>
> That is deliberate. Live data cannot validate a reasoning system, because you never find out
> whether it was right. Historical events where a known intervention changed one input and not
> the others are the only way to test whether the logic holds.

Point at the four regions.

> Situation, evidence, decision, explanation. Left to right, top to bottom — the layout is the
> workflow.

## 1:00–2:00 — The Diwali incident

> 27 October 2019, 23:30. Anand Vihar. **1,288 micrograms per cubic metre** of PM2.5. That is
> roughly twenty times the Indian daily standard.
>
> The officer's question is not "is this bad". It is "bad _because of what_, and what do I do".

Point at the transport geometry panel.

> The wind is arriving from 315 degrees — the north-west. Upwind, in the Punjab stubble belt,
> the satellite has detected fire activity in the last 24 hours.
>
> Note what this panel does **not** say. It does not say the fires caused this reading. It
> says the geometry is _consistent with_ transport toward Delhi. Those are very different
> claims, and only one of them is defensible.

_(Note: fires are drawn as an aggregate in the upwind sector at a representative transport
distance, not at true coordinates — the footer says so.)_

## 2:00–2:45 — The evidence

> Three hypotheses, evaluated independently.
>
> Fire and biomass: **moderate** evidence, on high-quality data. Traffic: **very weak**.
> Industry: **very weak**, on poor data.
>
> These do not add up to 100%, and the panel says so. They are not source shares — the
> hypotheses are not mutually exclusive. On a Diwali night in stubble season, fire and traffic
> evidence are both legitimately present.

Expand the Fire / Biomass row.

> Supporting observations, contradicting observations, and the historical validation for the
> module itself. And the likelihood ratio, with the words "not a probability" next to it,
> because it is not one.

## 2:45–3:30 — The recommendations

> Two recommendations. Each one carries a priority, the action, and the rule and policy that
> produced it.
>
> And at the top: **human review required** — with the reasons listed. The system is telling
> the officer that it does not consider itself sufficient here.
>
> Down here, "expected impact": reassess within six hours, and _why_ — the recommendation
> rests on satellite detections from the last 24 hours, which will have moved on. It gives a
> reassessment window. It never forecasts a concentration, and it says it cannot estimate the
> effect of the action it just recommended.

## 3:30–4:15 — Challenge the recommendation

Click **Why?**.

> This is the part that matters.
>
> Evidence, rule, policy, recommendation — the full trace, back from the advice to the
> observation. Supporting evidence on the left. **Contradicting evidence on the right, never
> hidden**, because the officer needs the counter-argument before someone else in the meeting
> supplies it.
>
> How far this can be pushed. The assumptions that must hold — including that satellite
> overpasses are periodic, so an absence of detections may be an absence of _overpass_ rather
> than an absence of fire. And the limitations: this is evidence of fire influence, not a
> measure of fire contribution. No microgram figure is attributed to biomass anywhere.
>
> An officer can take this into a meeting. More importantly, someone can use it to prove the
> system wrong.

Press Escape.

## 4:15–4:40 — Insufficient evidence

Click the **COVID lockdown** tab.

> April 2020. Traffic stopped by national order.
>
> Look what the system does. **Insufficient evidence.** No recommendation can be justified.
>
> Fire and weather observations were never collected for this window, so the biomass
> hypothesis cannot be judged — and the system refuses to guess. It says explicitly: this is a
> gap in our records, not a finding about the air. Not evidence that the air is clean, and not
> evidence that no action is needed.
>
> This state was designed, not fallen into. It is the behaviour the whole project exists to
> demonstrate.

_(If time is short, this is the section to protect. It is the differentiator.)_

## 4:40–5:00 — Close

> One more thing worth saying. Early on we built the obvious thing — a supervised classifier
> that predicts pollution source. It scored **98.6% accuracy**. We deleted it, because the
> labels were generated by our own rule, so the model had learned the rule, not the
> atmosphere. Every honesty instrument we could have pointed at it — SHAP, conformal
> prediction, calibration curves — would have made the fabrication _harder_ to detect, not
> easier.
>
> Most systems are designed to always give an answer. Vayu Console is designed to give an
> answer only when the evidence can support one — and to show exactly why.

---

## If something breaks

| Problem                                           | Do this                                                                        |
| ------------------------------------------------- | ------------------------------------------------------------------------------ |
| Console shows "Cannot reach the analysis service" | Render cold start; click **Try again**. The Diwali scenario needs no database. |
| You lose your place                               | `Present Incident` runs the full sequence hands-free.                          |
| Presentation Mode misbehaves                      | Escape exits and leaves the console fully drawn.                               |
| A judge asks something hard                       | [judge-faq.md](judge-faq.md)                                                   |
