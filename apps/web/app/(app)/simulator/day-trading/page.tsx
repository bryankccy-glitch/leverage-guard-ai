import type { Metadata } from "next";
import { PageTitle } from "@/features/common/PageTitle";
import { DayTradeSimulator } from "@/features/simulator/DayTradeSimulator";

export const metadata: Metadata = { title: "當沖風險模擬" };

export default function Page() {
  return (
    <>
      <PageTitle titleKey="nav.dayTrading" subtitle="現股當沖與融資使用不同的規則：不涉及維持率與追繳，而是沖銷、交割與強制買回。稅率依成交日期由規則引擎決定。" subtitleEn="Cash day trading follows different rules from margin: no maintenance ratio or margin call, but offsetting, settlement and forced buy-ins. The tax rate is set by the rule engine based on the trade date." />
      <DayTradeSimulator />
    </>
  );
}
