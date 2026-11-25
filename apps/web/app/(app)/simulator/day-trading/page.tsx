import type { Metadata } from "next";
import { PageTitle } from "@/features/common/PageTitle";
import { DayTradeSimulator } from "@/features/simulator/DayTradeSimulator";

export const metadata: Metadata = { title: "當沖風險模擬" };

export default function Page() {
  return (
    <>
      <PageTitle titleKey="nav.dayTrading" subtitle="現股當沖與融資使用不同的規則：不涉及維持率與追繳，而是沖銷、交割與強制買回。稅率依成交日期由規則引擎決定。" />
      <DayTradeSimulator />
    </>
  );
}
