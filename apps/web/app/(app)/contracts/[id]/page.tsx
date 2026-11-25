import { Suspense } from "react";
import { LoadingBlock } from "@/components/ui";
import { ContractById } from "@/features/contracts/routes";

export default function Page() {
  return (
    <Suspense fallback={<LoadingBlock rows={6} />}>
      <ContractById />
    </Suspense>
  );
}
