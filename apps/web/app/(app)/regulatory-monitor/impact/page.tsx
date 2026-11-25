import type { Metadata } from "next";
import { Suspense } from "react";
import { LoadingBlock } from "@/components/ui";
import { PageTitle } from "@/features/common/PageTitle";
import { UpdateDetailView } from "@/features/regulatory/Regulatory";

export const metadata: Metadata = { title: "影響分析" };

export default function Page() {
  return (
    <>
      <PageTitle titleKey="regulatory.impact" subtitleKey="regulatory.subtitle" />
      <Suspense fallback={<LoadingBlock rows={6} />}><UpdateDetailView /></Suspense>
    </>
  );
}
