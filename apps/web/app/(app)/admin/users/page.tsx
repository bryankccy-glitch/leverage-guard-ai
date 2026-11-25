import type { Metadata } from "next";
import { PageTitle } from "@/features/common/PageTitle";
import { UsersList } from "@/features/admin/Admin";

export const metadata: Metadata = { title: "使用者" };

export default function Page() {
  return (
    <>
      <PageTitle titleKey="admin.users" />
      <UsersList />
    </>
  );
}
