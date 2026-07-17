import type { Metadata } from "next";

import { ConsoleView } from "@/components/console-view";

export const metadata: Metadata = {
  title: "Operations Console",
  description: "Situation, evidence, decision and action for Delhi air quality.",
};

export default function ConsolePage() {
  return <ConsoleView />;
}
