import type { Metadata } from "next";
import { PageTitle } from "@/features/common/PageTitle";
import { NotificationsView } from "@/features/personal/Personal";

export const metadata: Metadata = { title: "通知" };

export default function Page() {
  return (
    <>
      <PageTitle titleKey="notifications.title" />
      <NotificationsView />
    </>
  );
}
