import type { Metadata } from "next";
import { PageTitle } from "@/features/common/PageTitle";
import { ReportList } from "@/features/reports/Reports";

export const metadata: Metadata = { title: "我的報告" };

export default function Page() {
  return (
    <>
      <PageTitle titleKey="reports.title" subtitleKey="reports.subtitle" />
      <ReportList />
    </>
  );
}
