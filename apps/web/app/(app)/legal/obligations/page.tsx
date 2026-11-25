import type { Metadata } from "next";
import { PageTitle } from "@/features/common/PageTitle";
import { RightsCenter } from "@/features/legal/Legal";

export const metadata: Metadata = { title: "投資人義務" };

export default function Page() {
  return (
    <>
      <PageTitle titleKey="timeline.investorObligations" subtitleKey="legal.rightsDesc" />
      <RightsCenter kind="obligations" />
    </>
  );
}
