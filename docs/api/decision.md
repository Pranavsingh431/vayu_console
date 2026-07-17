# Decision API

Read-only. Turns Evidence Reports into recommendations.
See [../architecture/decision-engine.md](../architecture/decision-engine.md) for design.

Base: `/decision`

| Method | Path                        | Purpose                                     |
| ------ | --------------------------- | ------------------------------------------- |
| GET    | `/decision/example`         | A worked Decision Report (Diwali 2019)      |
| GET    | `/decision/example/explain` | "Why this recommendation?" for each item    |
| POST   | `/decision/evaluate`        | Evidence Report → Decision Report           |
| GET    | `/decision/policies`        | Policy families                             |
| GET    | `/decision/recommendations` | The full catalogue                          |
| GET    | `/decision/rules`           | Every rule and why it is defensible         |
| GET    | `/decision/gaps`            | Categories with no recommendations, and why |

---

## POST /decision/evaluate

Accepts an `EvidenceReport` (exactly the body `POST /evidence/evaluate` returns) and
returns a `DecisionReport`. The engine reads nothing else — no database, no raw data.

### Request

```bash
curl -X POST http://localhost:8000/decision/evaluate \
  -H 'Content-Type: application/json' \
  -d "$(curl -s -X POST http://localhost:8000/evidence/evaluate \
        -H 'Content-Type: application/json' \
        -d '{"station_id": 83, "at": "2019-10-27T18:00:00Z"}')"
```

### Response (abridged)

```json
{
  "timestamp": "2019-10-27T18:00:00Z",
  "station": "Anand Vihar, Delhi - DPCC-10487",
  "overall_status": "action_recommended",
  "summary": "2 recommendation(s) supported by evidence.",
  "data_quality": "poor",
  "requires_human_review": true,
  "human_review_reasons": [
    "Data quality is poor. The evidence may be based on sparse or missing observations.",
    "Historical validation is still pending for: Diwali 2019 (discriminant validity)"
  ],
  "conflict_note": null,
  "recommendations": [
    {
      "id": "REC_PUBLIC_ADVISORY",
      "title": "Issue a public health advisory for the affected zone",
      "category": "public_health",
      "priority": "high",
      "action": "Issue an advisory recommending that residents limit outdoor exertion...",
      "reason": "An advisory is defensible on the measured concentration alone...\n\nScope: Does NOT justify emergency resource deployment.",
      "supporting_evidence": [
        {
          "label": "1593 fire detections upwind within 24h",
          "value": 1593,
          "source": "firms_viirs_snpp_sp"
        }
      ],
      "contradicting_evidence": [
        {
          "label": "Boundary layer height",
          "value": 210,
          "unit": "m",
          "source": "open_meteo_archive"
        }
      ],
      "confidence_note": "The strongest recommendation this engine makes, because it rests on a measured concentration rather than on an inferred source.",
      "triggered_by_rule": "FIRE_002",
      "policy": "PUBLIC_HEALTH",
      "decision_trace": [
        {
          "step": "evidence",
          "identifier": "biomass",
          "detail": "biomass evidence: moderate ★★★ ..."
        },
        {
          "step": "rule",
          "identifier": "FIRE_002",
          "detail": "Moderate biomass evidence. Defensible because: ..."
        },
        {
          "step": "policy",
          "identifier": "PUBLIC_HEALTH",
          "detail": "Policy PUBLIC_HEALTH applies."
        },
        {
          "step": "recommendation",
          "identifier": "REC_PUBLIC_ADVISORY",
          "detail": "Issue a public health advisory..."
        }
      ]
    }
  ],
  "engine_version": "0.1.0",
  "evidence_engine_version": "0.1.0"
}
```

### Notes

- **`confidence_note`, never `confidence_score`.** Prose, not a number. A number would
  imply a precision the underlying evidence does not have.
- **`contradicting_evidence` is always populated** where the evidence module supplied any.
  An officer needs the counter-argument before someone else raises it.
- **`overall_status`** distinguishes `insufficient_evidence` (we could not look) from
  `no_recommendation` (we looked, nothing warranted). These are not the same, and merging
  them would let a blind sensor read as a clean bill of health.

---

## GET /decision/example/explain

Powers the UI's _Challenge Recommendation_ feature. Returns, per recommendation:

```json
[
  {
    "recommendation": "Issue a public health advisory for the affected zone",
    "why": "An advisory is defensible on the measured concentration alone...",
    "supporting_evidence": [...],
    "contradicting_evidence": [...],
    "assumptions": ["FIRMS detections are treated as a proxy for emissions..."],
    "limitations": ["The advisory does not reduce emissions..."],
    "confidence_note": "...",
    "decision_trace": [...],
    "how_to_challenge": "Check the contradicting evidence and the assumptions first. If an assumption does not hold at this station, the recommendation does not follow."
  }
]
```

---

## Status codes

| Code | Meaning                                                                           |
| ---- | --------------------------------------------------------------------------------- |
| 200  | A report was produced. May contain zero recommendations — that is a valid answer. |
| 422  | The Evidence Report body did not validate.                                        |

There is no 404 and no "no data" error: an Evidence Report with nothing in it yields a
Decision Report with `overall_status: insufficient_evidence`. Being unable to see is a
finding, not a failure.
