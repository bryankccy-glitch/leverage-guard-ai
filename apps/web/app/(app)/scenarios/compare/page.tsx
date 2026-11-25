import type { Metadata } from "next";
import { PageTitle } from "@/features/common/PageTitle";
import { ScenarioCompare } from "@/features/scenarios/Lab";

export const metadata: Metadata = { title: "情境比較" };

export default function Page() {
  return (
    <>
      <PageTitle titleKey="lab.compare" subtitleKey="lab.compareDesc" />
      <ScenarioCompare />
    </>
  );
}
