/**
 * Demo Mode scenarios.
 *
 * Each scenario is a real station-hour from ingested data — not a fixture. The
 * console calls the same `/evidence/evaluate` and `/decision/evaluate` endpoints a
 * live user would, so what a judge sees is the system working, not a mock.
 *
 * Two are deliberately incomplete, and that is the point:
 *
 * - COVID 2020 and Odd-Even II 2016 were ingested WITHOUT fires or weather. The
 *   biomass module will honestly report insufficient evidence there. That is the
 *   system saying "I cannot see" rather than guessing, which is the behaviour the
 *   whole project exists to demonstrate.
 * - GRAP is absent. It is a threshold-triggered regime rather than a dated event,
 *   and we never ingested one. Including it would mean inventing it.
 */

export interface Scenario {
  id: string;
  label: string;
  /** What an officer would have been facing. One line, no jargon. */
  situation: string;
  /** Instant to explain, UTC. */
  at: string;
  /** Fires and weather ingested? Drives the honest "partial data" note. */
  complete: boolean;
  /** What this scenario demonstrates. Shown in Demo Mode, said in the demo. */
  demonstrates: string;
  /** Year, to highlight the matching timeline card. */
  year: number;
}

/** The worked example the API serves from a fixed context — always available. */
export const DIWALI_EXAMPLE: Scenario = {
  id: "diwali-2019",
  label: "Diwali 2019",
  situation: "Firework night during peak stubble season. Two explanations arrive together.",
  at: "2019-10-27T18:00:00Z",
  complete: true,
  demonstrates:
    "Strong fire evidence with weak traffic evidence. The engine addresses both without choosing between them.",
  year: 2019,
};

export const COVID: Scenario = {
  id: "covid-2020",
  label: "COVID lockdown",
  situation:
    "Traffic stopped by national order. The intervention that calibrated the traffic module.",
  at: "2020-04-15T03:30:00Z",
  complete: false,
  demonstrates:
    "NO₂ fell 54% while SO₂ held flat — power generation stayed essential. The differential that let the traffic hypothesis survive a test it could have failed.",
  year: 2020,
};

export const ODD_EVEN: Scenario = {
  id: "odd-even-2016",
  label: "Odd-Even II",
  situation: "Private cars restricted, April 2016. No stubble, no winter inversion.",
  at: "2016-04-20T03:30:00Z",
  complete: false,
  demonstrates:
    "The only unconfounded vehicle window we have. Weak treatment on few stations — the engine reports what it can and no more.",
  year: 2016,
};

export const SCENARIOS: Scenario[] = [DIWALI_EXAMPLE, COVID, ODD_EVEN];

/**
 * Deliberately not a scenario.
 *
 * Surfaced in the UI so its absence reads as a decision rather than an oversight —
 * the same reason the API exposes `/decision/gaps`.
 */
export const UNAVAILABLE_SCENARIOS: Array<{ label: string; reason: string }> = [
  {
    label: "GRAP",
    reason:
      "GRAP is a threshold-triggered regime, not a dated event, so there is no single station-hour to reconstruct. Adding it would mean inventing an episode.",
  },
];
