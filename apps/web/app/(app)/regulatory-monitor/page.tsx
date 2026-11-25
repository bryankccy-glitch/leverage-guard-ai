import type { Metadata } from "next";
import { PageTitle } from "@/features/common/PageTitle";
import { RegulatoryHome } from "@/features/regulatory/Regulatory";

export const metadata: Metadata = { title: "法規變動監察" };

export default function Page() {
  return (
    <>
      <PageTitle titleKey="regulatory.title" subtitleKey="regulatory.subtitle" />
      <RegulatoryHome />
    </>
  );
}
