import type { Metadata } from "next";
import { PageTitle } from "@/features/common/PageTitle";
import { AdminHome } from "@/features/admin/Admin";

export const metadata: Metadata = { title: "管理後台" };

export default function Page() {
  return (
    <>
      <PageTitle titleKey="admin.title" />
      <AdminHome />
    </>
  );
}
