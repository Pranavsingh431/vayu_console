# Officer Decision Engine

> Turns Evidence Reports into transparent, deterministic, defensible recommendations.
> No model. No language model. No probabilities.

Implemented in `apps/api/app/decision/`. Consumes the Evidence Engine
([evidence-engine.md](evidence-engine.md)) and nothing else.

---

## 1. The governing test

Every rule and every catalogue entry was written against one question:

> **Could a pollution control officer defend this in a meeting?**

If the answer is no, it does not exist. This is why the catalogue is short. Several
obvious-sounding recommendations were deliberately excluded:

| Excluded              | Why                                                                                                                                                           |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| "Halt construction"   | No construction evidence module exists. Phase 2 restricted the hypotheses to biomass, traffic and industrial, so this would be advice with nothing behind it. |
| "Close schools"       | Needs a health exposure threshold we have not established. PM2.5 alone does not carry one an officer could cite.                                              |
| "Inspect the plant"   | No natural experiment isolates industry, so the module carries no likelihood ratio. The operator would be right to object.                                    |
| "Ban stubble burning" | Outside Delhi's jurisdiction. An officer cannot act on it, so it is a complaint, not a recommendation.                                                        |

`GET /decision/gaps` exposes empty categories and their reasons, so a gap reads as a
decision rather than an oversight.

---

## 2. Data flow

```
EvidenceReport            (from the Evidence Engine — never raw data)
      ↓
  Rule Engine             deterministic conditions over evidence strength
      ↓
  Policy                  EMERGENCY_RESPONSE / PUBLIC_HEALTH / TRAFFIC_MANAGEMENT / MONITORING / NO_ACTION
      ↓
  Recommendation          from a fixed catalogue, with evidence attached
      ↓
  DecisionReport          + conflict note, human review flags, decision trace
```

The engine **never queries the database**. If a fact is not in the Evidence Report, the
engine cannot use it — which is what guarantees every recommendation traces back to an
observation.

---

## 3. Two invariants that hold across every rule

### 3.1 Rules fire on the PRESENCE of evidence, never its absence

"Biomass evidence is weak" must never trigger a traffic recommendation.

This is not pedantry. Verified in our own data:

```
2019-10-30   2,600 fire detections
2019-10-31       4      <-- the satellite blinked; fires did not stop
2019-11-03   2,612
```

Stubble burning does not pause for a day. Those near-zero days are cloud cover or a
missed overpass. A rule reasoning from "no fires detected" would have an officer act on
a cloudy sky.

`at_most()` therefore returns **False** for insufficient evidence: a hypothesis we could
not judge is not "at most weak", it is unknown, and treating unknown as low is exactly
how absence turns into a conclusion.

### 3.2 Rules never choose between competing hypotheses

If two hypotheses are moderate or stronger, **both** sets of recommendations are emitted
and the conflict is reported. Choosing would be source apportionment by the back door —
the thing Phase 2 established we cannot do.

On a Diwali night in stubble season, fireworks and transported smoke arrive together.
Both being true is the correct answer.

---

## 4. The rules

| Rule             | Fires when                                        | Policy             | Explicitly does NOT imply                                   |
| ---------------- | ------------------------------------------------- | ------------------ | ----------------------------------------------------------- |
| `FIRE_001`       | biomass ≥ STRONG **and** traffic ≤ WEAK           | EMERGENCY_RESPONSE | that traffic is absent, or any quantified fire contribution |
| `FIRE_002`       | biomass = MODERATE                                | PUBLIC_HEALTH      | that emergency resources are warranted                      |
| `TRAFFIC_001`    | traffic ≥ MODERATE **and** hour is a commute peak | TRAFFIC_MANAGEMENT | that traffic is dominant (LR 2.11, weak)                    |
| `INDUSTRIAL_001` | industrial ≥ WEAK (i.e. SO2 actually measured)    | MONITORING         | any inspection, restriction or enforcement                  |

**Rules that deliberately do not exist:**

- _Traffic strong outside a commute peak._ The traffic module caps at MODERATE by
  construction, and elevated NO₂ at 23:00 IST is not a commute profile — the module
  reports that hour as contradicting evidence. Rush-hour enforcement at midnight is not
  defensible.
- _Industrial insufficient → "do not inspect"._ The engine does state this, but as a
  report-level limitation rather than a recommendation. A "recommendation" to do nothing
  is not an action; putting it in the list would pad the list while telling the officer
  nothing.

---

## 5. Decision trace

Every recommendation carries a four-step trace, walkable backwards from advice to
observation:

```
EVIDENCE       biomass: strong ★★★★ (quality good, identification strong)
   ↓
RULE           FIRE_001 — strong biomass with traffic no greater than weak.
               Defensible because: fires were observed upwind by satellite, a
               signal independent of the monitor being explained.
   ↓
POLICY         EMERGENCY_RESPONSE
   ↓
RECOMMENDATION REC_SPRINKLER — Deploy roadside water sprinklers on arterial routes
```

`GET /decision/example/explain` returns this plus supporting evidence, **contradicting
evidence**, assumptions and limitations — powering the UI's _Challenge Recommendation_
affordance.

Contradicting evidence is never optional. An officer challenged in a meeting needs the
counter-argument before someone else supplies it.

---

## 6. Human review

`requires_human_review` is set when any of these hold:

| Trigger                       | Why it matters                                               |
| ----------------------------- | ------------------------------------------------------------ |
| Data quality POOR or NO_DATA  | The evidence may rest on sparse or missing observations.     |
| Conflicting strong evidence   | The engine cannot separate the hypotheses and does not try.  |
| Any hypothesis insufficient   | We could not look. Not evidence the source is absent.        |
| Historical validation pending | The module has not yet survived a test that could reject it. |
| No rule fired                 | Nothing to suggest — which is not the same as nothing to do. |

In practice this fires on most reports today, because biomass validation is still
PENDING. That is correct: the flag is honest, not decorative.

---

## 7. Overall status

`INSUFFICIENT_EVIDENCE` and `NO_RECOMMENDATION` are deliberately distinct:

- **INSUFFICIENT_EVIDENCE** — we could not look. Required observations are missing.
- **NO_RECOMMENDATION** — we looked, and nothing in the catalogue is warranted.

Merging them would let a blind sensor read as a clean bill of health.

---

## 8. Worked example — Diwali 2019, Anand Vihar, 23:30 IST

```
status  : action_recommended        quality: poor      human_review: true

  [high    ] Issue a public health advisory for the affected zone
             rule=FIRE_002  policy=PUBLIC_HEALTH
  [routine ] Increase monitoring cadence at the affected station
             rule=FIRE_002  policy=MONITORING

human review reasons:
  - Data quality is poor. The evidence may be based on sparse or missing observations.
  - Historical validation is still pending for: Diwali 2019 (discriminant validity), ...
```

Note what is **absent**: no traffic recommendation, because 23:30 IST is not a commute
peak — even though NO₂ was elevated at 114 µg/m³. The engine declines to recommend
rush-hour enforcement at midnight.

---

## 9. Limitations

1. **The engine cannot estimate the effect of any recommendation.** It cannot say
   sprinkling will remove N µg/m³. No such estimate is possible from our data
   (`inference.md` §1).
2. **Recommendations inherit every limitation of the evidence beneath them.** A traffic
   recommendation is only as identified as the traffic module, which is weak (LR 2.11,
   and that is an upper bound).
3. **The catalogue is small and Delhi-specific.** Sprinkling fleets and PUC teams are
   assumed to exist.
4. **No prioritisation across recommendations beyond `Priority`.** The engine does not
   know the officer's budget or staffing.
5. **The CONSTRUCTION category is empty** and will stay so until a construction evidence
   module exists and survives a stress test.

---

## 10. Extension points

- **A new rule:** add a `Rule` to `app/decision/rules/rules.py` and include it in
  `ALL_RULES`. It must declare `defensible_because` — the tests enforce this.
- **A new recommendation:** add a `CatalogueEntry` to
  `app/decision/recommendations/catalogue.py`. It must carry a `confidence_note`, never a
  score.
- **A new policy:** extend the `Policy` enum and `_POLICY_DESCRIPTIONS`.
- **Replacing the rule engine:** `DecisionEngine(rule_engine=RuleEngine(rules=(...)))` —
  tested, so rules can be swapped wholesale without touching the engine.

Before adding anything, ask the question in §1.
