import type { Metadata } from "next";
import { PageTitle } from "@/features/common/PageTitle";
import { ContractCompare } from "@/features/contracts/Contracts";

export const metadata: Metadata = { title: "契約比較" };

export default function Page() {
  return (
    <>
      <PageTitle titleKey="contracts.compare" subtitleKey="contracts.compareNote" />
      <ContractCompare />
    </>
  );
}
