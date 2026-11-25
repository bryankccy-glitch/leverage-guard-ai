import type { Metadata } from "next";
import { PageTitle } from "@/features/common/PageTitle";
import { KnowledgeBase } from "@/features/admin/Admin";

export const metadata: Metadata = { title: "知識庫" };

export default function Page() {
  return (
    <>
      <PageTitle titleKey="admin.knowledge" />
      <KnowledgeBase />
    </>
  );
}
