import type { Metadata } from "next";
import { PageTitle } from "@/features/common/PageTitle";
import { RightsCenter } from "@/features/legal/Legal";

export const metadata: Metadata = { title: "權利與義務" };

export default function Page() {
  return (
    <>
      <PageTitle titleKey="legal.rightsTitle" subtitleKey="legal.rightsDesc" />
      <RightsCenter />
    </>
  );
}
