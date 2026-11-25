import type { Metadata } from "next";
import { PageTitle } from "@/features/common/PageTitle";
import { SystemHealth } from "@/features/admin/Admin";

export const metadata: Metadata = { title: "系統健康" };

export default function Page() {
  return (
    <>
      <PageTitle titleKey="admin.health" />
      <SystemHealth />
    </>
  );
}
