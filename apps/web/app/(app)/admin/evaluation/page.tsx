import type { Metadata } from "next";
import { PageTitle } from "@/features/common/PageTitle";
import { Evaluation } from "@/features/admin/Admin";

export const metadata: Metadata = { title: "評估" };

export default function Page() {
  return (
    <>
      <PageTitle titleKey="admin.evaluation" />
      <Evaluation />
    </>
  );
}
