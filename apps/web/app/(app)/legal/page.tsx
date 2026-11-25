import type { Metadata } from "next";
import { PageTitle } from "@/features/common/PageTitle";
import { LegalHome } from "@/features/legal/Legal";

export const metadata: Metadata = { title: "法律知識中心" };

export default function Page() {
  return (
    <>
      <PageTitle titleKey="legal.title" subtitleKey="legal.subtitle" />
      <LegalHome />
    </>
  );
}
