import type { Metadata } from "next";
import { PageTitle } from "@/features/common/PageTitle";
import { RulesTable } from "@/features/admin/Admin";

export const metadata: Metadata = { title: "法律規則" };

export default function Page() {
  return (
    <>
      <PageTitle titleKey="admin.rules" />
      <RulesTable />
    </>
  );
}
