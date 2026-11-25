import type { Metadata } from "next";
import { Suspense } from "react";
import { LoadingBlock } from "@/components/ui";
import { PageTitle } from "@/features/common/PageTitle";
import { LegalSearch } from "@/features/legal/Legal";

export const metadata: Metadata = { title: "法規搜尋" };

export default function Page() {
  return (
    <>
      <PageTitle titleKey="legal.title" subtitleKey="legal.subtitle" />
      <Suspense fallback={<LoadingBlock rows={6} />}><LegalSearch /></Suspense>
    </>
  );
}
