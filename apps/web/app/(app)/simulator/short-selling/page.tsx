import type { Metadata } from "next";
import { NotAvailable } from "@/components/ui";
import { PageTitle } from "@/features/common/PageTitle";

export const metadata: Metadata = { title: "融券模擬" };

export default function Page() {
  return (
    <>
      <PageTitle titleKey="nav.simulation" subtitle="融券交易屬於第二階段（P2）擴充範圍，規則與計算尚未建立，因此不提供試算。" subtitleEn="Short selling is in the phase-two (P2) scope. Its rules and calculations are not built yet, so no simulation is offered." />
      <NotAvailable phase="P2" />
    </>
  );
}
