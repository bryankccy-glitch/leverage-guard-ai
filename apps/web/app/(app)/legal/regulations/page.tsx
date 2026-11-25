import type { Metadata } from "next";
import { PageTitle } from "@/features/common/PageTitle";
import { LegalHome } from "@/features/legal/Legal";

export const metadata: Metadata = { title: "法規清單" };

export default function Page() {
  return (
    <>
      <PageTitle titleKey="legal.documents" subtitleKey="legal.subtitle" />
      <LegalHome />
    </>
  );
}
