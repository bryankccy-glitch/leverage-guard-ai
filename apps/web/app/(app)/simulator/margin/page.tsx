import type { Metadata } from "next";
import { PageTitle } from "@/features/common/PageTitle";
import { MarginSimulator } from "@/features/simulator/MarginSimulator";

export const metadata: Metadata = { title: "融資風險模擬" };

export default function Page() {
  return (
    <>
      <PageTitle titleKey="nav.margin" subtitle="輸入或拖動股價，同步看到損益、擔保維持率、追繳條件與法律依據。所有數字都是模擬，不是投資建議。" subtitleEn="Type or drag the price to see P&L, maintenance ratio, margin call conditions and the legal basis update together. All numbers are simulated and are not investment advice." />
      <MarginSimulator />
    </>
  );
}
