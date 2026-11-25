import type { Metadata } from "next";
import { PageTitle } from "@/features/common/PageTitle";
import { AuditLogs } from "@/features/admin/Admin";

export const metadata: Metadata = { title: "稽核紀錄" };

export default function Page() {
  return (
    <>
      <PageTitle titleKey="admin.audit" />
      <AuditLogs />
    </>
  );
}
