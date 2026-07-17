/**
 * Evidence and Decision contracts.
 *
 * Mirrors `apps/api/app/evidence/schemas/evidence.py` and
 * `apps/api/app/decision/schemas/decision.py`.
 *
 * Two things the UI must never do, encoded here so the types push back:
 * - There is no probability or percentage anywhere. Source contribution is not
 *   measurable from our data, so any number shaped like a share is fabricated.
 * - Evidence strengths do NOT sum to 1. Never render them as a pie chart or a
 *   stacked bar; two hypotheses can both be strong and both be right.
 */

export type Hypothesis = "biomass" | "traffic" | "industrial";

/** `insufficient_evidence` means we could not look — NOT that the source is absent. */
export type EvidenceStrength =
  "insufficient_evidence" | "very_weak" | "weak" | "moderate" | "strong" | "very_strong";

/** Deliberately orthogonal to strength: strong evidence on poor data is a real state. */
export type EvidenceQuality = "no_data" | "poor" | "fair" | "good" | "high";

export type ValidationStatus = "accepted" | "rejected" | "uncertain" | "pending";

/** How well the data identifies the hypothesis at all. A property of the design. */
export type Identification = "strong" | "weak" | "very_weak" | "unidentified";

export interface Observation {
  label: string;
  value: number | string | null;
  unit: string | null;
  source: string;
  observed_at: string | null;
}

export interface HistoricalValidation {
  experiment: string;
  status: ValidationStatus;
  detail: string;
  likelihood_ratio: number | null;
}

export interface EvidenceResult {
  name: string;
  hypothesis: Hypothesis;
  status: EvidenceStrength;
  strength: EvidenceStrength;
  evidence_quality: EvidenceQuality;
  identification: Identification;
  stars: string;
  explanation: string;
  likelihood_ratio: number | null;
  supporting_observations: Observation[];
  /** Never empty by accident. The counter-argument is part of the evidence. */
  contradicting_observations: Observation[];
  assumptions: string[];
  limitations: string[];
  historical_validation: HistoricalValidation[];
  references: string[];
}

export interface EvidenceReport {
  station: string;
  station_id: number | null;
  evaluated_at: string;
  /** The measured concentration being explained. Not evidence — the observed fact. */
  measured_pm25: number | null;
  generated_at: string;
  evidence: EvidenceResult[];
  summary: string;
  overall_quality: EvidenceQuality;
  assumptions: string[];
  limitations: string[];
  engine_version: string;
  data_sources: string[];
}

// --- Decision -------------------------------------------------------------

export type RecommendationCategory =
  | "road_traffic"
  | "construction"
  | "industrial_monitoring"
  | "public_health"
  | "emergency_response"
  | "monitoring_only";

export type Policy =
  "EMERGENCY_RESPONSE" | "PUBLIC_HEALTH" | "TRAFFIC_MANAGEMENT" | "MONITORING" | "NO_ACTION";

export type Priority = "immediate" | "high" | "routine" | "informational";

/**
 * `insufficient_evidence` (we could not look) is distinct from
 * `no_recommendation` (we looked, nothing warranted). Never merge them in the UI:
 * a blind sensor would read as a clean bill of health.
 */
export type OverallStatus =
  "action_recommended" | "monitor" | "no_recommendation" | "insufficient_evidence";

export type DecisionTraceStep = "evidence" | "rule" | "policy" | "recommendation";

export interface TraceEntry {
  step: DecisionTraceStep;
  identifier: string;
  detail: string;
}

export interface Recommendation {
  id: string;
  title: string;
  category: RecommendationCategory;
  priority: Priority;
  action: string;
  reason: string;
  supporting_evidence: Observation[];
  contradicting_evidence: Observation[];
  assumptions: string[];
  limitations: string[];
  /** Prose, never a number. A score would imply a precision we do not have. */
  confidence_note: string;
  references: string[];
  decision_trace: TraceEntry[];
  triggered_by_rule: string;
  policy: Policy;
}

export interface DecisionReport {
  timestamp: string;
  generated_at: string;
  station: string;
  station_id: number | null;
  overall_status: OverallStatus;
  summary: string;
  recommendations: Recommendation[];
  assumptions: string[];
  limitations: string[];
  supporting_evidence: Observation[];
  contradicting_evidence: Observation[];
  data_quality: EvidenceQuality;
  requires_human_review: boolean;
  human_review_reasons: string[];
  decision_trace: TraceEntry[];
  conflict_note: string | null;
  engine_version: string;
  evidence_engine_version: string;
}

// --- Display helpers ------------------------------------------------------

/** Kass & Raftery bands, rendered. Five slots so the scale reads consistently. */
export const STRENGTH_STARS: Record<EvidenceStrength, string> = {
  insufficient_evidence: "☆☆☆☆☆",
  very_weak: "★☆☆☆☆",
  weak: "★★☆☆☆",
  moderate: "★★★☆☆",
  strong: "★★★★☆",
  very_strong: "★★★★★",
};

export const STRENGTH_LABEL: Record<EvidenceStrength, string> = {
  insufficient_evidence: "Cannot judge",
  very_weak: "Very weak",
  weak: "Weak",
  moderate: "Moderate",
  strong: "Strong",
  very_strong: "Very strong",
};

export const HYPOTHESIS_LABEL: Record<Hypothesis, string> = {
  biomass: "Fire / Biomass",
  traffic: "Traffic",
  industrial: "Industry / Power",
};
