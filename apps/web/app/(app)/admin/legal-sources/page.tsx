import type { Metadata } from "next";
import { PageTitle } from "@/features/common/PageTitle";
import { LegalSources } from "@/features/admin/Admin";

export const metadata: Metadata = { title: "法律資料來源" };

export default function Page() {
  return (
    <>
      <PageTitle titleKey="admin.sources" />
      <LegalSources />
    </>
  );
}
