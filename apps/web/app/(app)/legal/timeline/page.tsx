import type { Metadata } from "next";
import { PageTitle } from "@/features/common/PageTitle";
import { LegalTimelinePage } from "@/features/legal/Legal";

export const metadata: Metadata = { title: "法律責任時間軸" };

export default function Page() {
  return (
    <>
      <PageTitle titleKey="timeline.title" subtitleKey="legal.timelineDesc" />
      <LegalTimelinePage />
    </>
  );
}
