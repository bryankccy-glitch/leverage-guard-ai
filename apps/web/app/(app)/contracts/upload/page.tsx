import type { Metadata } from "next";
import { PageTitle } from "@/features/common/PageTitle";
import { ContractUpload } from "@/features/contracts/Contracts";

export const metadata: Metadata = { title: "上傳契約" };

export default function Page() {
  return (
    <>
      <PageTitle titleKey="contracts.upload" subtitleKey="contracts.subtitle" />
      <ContractUpload />
    </>
  );
}
