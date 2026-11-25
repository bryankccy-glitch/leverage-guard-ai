import type { Metadata } from "next";
import { PageTitle } from "@/features/common/PageTitle";
import { ScenarioList } from "@/features/scenarios/Lab";

export const metadata: Metadata = { title: "極端情境實驗室" };

export default function Page() {
  return (
    <>
      <PageTitle titleKey="lab.title" subtitleKey="lab.subtitle" />
      <ScenarioList />
    </>
  );
}
