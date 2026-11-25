import type { Metadata } from "next";
import { PageTitle } from "@/features/common/PageTitle";
import { ContractList } from "@/features/contracts/Contracts";

export const metadata: Metadata = { title: "契約分析" };

export default function Page() {
  return (
    <>
      <PageTitle titleKey="contracts.title" subtitleKey="contracts.subtitle" />
      <ContractList />
    </>
  );
}
