import type { Metadata } from "next";
import { PortfolioCalc } from "@/features/simulator/PortfolioCalc";

export const metadata: Metadata = { title: "整戶維持率試算" };

export default function Page() {
  return <PortfolioCalc />;
}
