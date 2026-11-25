import type { Metadata } from "next";
import { PageTitle } from "@/features/common/PageTitle";
import { HistoryView } from "@/features/personal/Personal";

export const metadata: Metadata = { title: "數位分身紀錄" };

export default function Page() {
  return (
    <>
      <PageTitle titleKey="history.title" subtitleKey="history.subtitle" />
      <HistoryView />
    </>
  );
}
