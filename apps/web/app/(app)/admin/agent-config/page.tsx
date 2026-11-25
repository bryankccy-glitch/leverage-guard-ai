import type { Metadata } from "next";
import { PageTitle } from "@/features/common/PageTitle";
import { AgentConfig } from "@/features/admin/Admin";

export const metadata: Metadata = { title: "Agent 設定" };

export default function Page() {
  return (
    <>
      <PageTitle titleKey="admin.agentConfig" />
      <AgentConfig />
    </>
  );
}
