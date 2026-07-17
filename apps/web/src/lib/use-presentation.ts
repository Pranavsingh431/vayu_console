"use client";

import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Presentation Mode: the console walks itself through an incident.
 *
 * A judge sees the whole reasoning chain unfold in ~35 seconds without anyone
 * touching the keyboard — situation, then wind, then fires, then evidence, then
 * recommendations, then the Challenge modal opening on its own.
 *
 * The order is the argument, not a slideshow: each step only makes sense because
 * the one before it landed. Evidence cannot appear before the fires it rests on.
 */

export const STEPS = [
  "situation",
  "wind",
  "fires",
  "evidence",
  "recommendations",
  "challenge",
  "timeline",
  "done",
] as const;

export type PresentationStep = (typeof STEPS)[number];

/**
 * Dwell time per step, ms. Long enough to read the thing that just appeared,
 * short enough that a judge never wonders whether it has frozen. `challenge`
 * holds longest because the modal is the point of the product.
 */
const DWELL: Record<PresentationStep, number> = {
  situation: 3200,
  wind: 2600,
  fires: 3000,
  evidence: 5000,
  recommendations: 5000,
  challenge: 11000,
  timeline: 5000,
  done: 0,
};

export interface Presentation {
  active: boolean;
  step: PresentationStep;
  /** Whether a stage has been reached — drives reveal, not a boolean per panel. */
  reached: (step: PresentationStep) => boolean;
  start: () => void;
  stop: () => void;
  progress: number;
}

const index = (s: PresentationStep) => STEPS.indexOf(s);

export function usePresentation(): Presentation {
  const [active, setActive] = useState(false);
  const [step, setStep] = useState<PresentationStep>("done");
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clear = useCallback(() => {
    if (timer.current) {
      clearTimeout(timer.current);
      timer.current = null;
    }
  }, []);

  const stop = useCallback(() => {
    clear();
    setActive(false);
    // Land on `done`, which reveals everything. Stopping the tour must never
    // leave the console half-drawn — an officer interrupting a demo still needs
    // a working screen.
    setStep("done");
  }, [clear]);

  const start = useCallback(() => {
    clear();
    setActive(true);
    setStep("situation");
  }, [clear]);

  useEffect(() => {
    if (!active || step === "done") return;

    const next = STEPS[index(step) + 1];
    timer.current = setTimeout(() => {
      if (next === "done") {
        setActive(false);
        setStep("done");
      } else {
        setStep(next);
      }
    }, DWELL[step]);

    return clear;
  }, [active, step, clear]);

  // Escape must always exit. A presenter who loses control of the screen in front
  // of judges is worse off than one who never started it.
  useEffect(() => {
    if (!active) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") stop();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [active, stop]);

  useEffect(() => clear, [clear]);

  const reached = useCallback(
    (target: PresentationStep) => !active || index(step) >= index(target),
    [active, step],
  );

  const total = STEPS.length - 1;
  return {
    active,
    step,
    reached,
    start,
    stop,
    progress: active ? index(step) / total : 1,
  };
}
