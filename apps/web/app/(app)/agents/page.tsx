import type { Metadata } from "next";
import { PageTitle } from "@/features/common/PageTitle";
import { AgentsCenter } from "@/features/agents/AgentsCenter";

export const metadata: Metadata = { title: "AI Agent 中心" };

export default function Page() {
  return (
    <>
      <PageTitle titleKey="agents.title" subtitleKey="agents.subtitle" />
      <AgentsCenter />
    </>
  );
}
