import type { Metadata } from "next";
import { PageTitle } from "@/features/common/PageTitle";
import { ReviewQueue } from "@/features/admin/Admin";

export const metadata: Metadata = { title: "審查佇列" };

export default function Page() {
  return (
    <>
      <PageTitle titleKey="admin.reviewQueue" />
      <ReviewQueue />
    </>
  );
}
