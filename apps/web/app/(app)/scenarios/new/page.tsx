import type { Metadata } from "next";
import { Suspense } from "react";
import { LoadingBlock } from "@/components/ui";
import { PageTitle } from "@/features/common/PageTitle";
import { ScenarioBuilder } from "@/features/scenarios/Lab";

export const metadata: Metadata = { title: "建立情境" };

export default function Page() {
  return (
    <>
      <PageTitle titleKey="lab.title" subtitleKey="lab.subtitle" />
      <Suspense fallback={<LoadingBlock rows={6} />}>
        <ScenarioBuilder />
      </Suspense>
    </>
  );
}
