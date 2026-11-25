import type { Metadata } from "next";
import { PageTitle } from "@/features/common/PageTitle";
import { DisputesPage } from "@/features/legal/Legal";

export const metadata: Metadata = { title: "爭議與求助" };

export default function Page() {
  return (
    <>
      <PageTitle titleKey="legal.disputesTitle" subtitleKey="legal.disputesDesc" />
      <DisputesPage />
    </>
  );
}
