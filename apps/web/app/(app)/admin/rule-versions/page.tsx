import type { Metadata } from "next";
import { PageTitle } from "@/features/common/PageTitle";
import { RulesTable } from "@/features/admin/Admin";

export const metadata: Metadata = { title: "規則版本" };

export default function Page() {
  return (
    <>
      <PageTitle titleKey="admin.ruleVersions" />
      <RulesTable versionsOnly />
    </>
  );
}
