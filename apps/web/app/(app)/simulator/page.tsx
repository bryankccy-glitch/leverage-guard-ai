import type { Metadata } from "next";
import { SimulatorIndex } from "@/features/simulator/SimulatorIndex";

export const metadata: Metadata = { title: "風險模擬" };

export default function Page() {
  return <SimulatorIndex />;
}
