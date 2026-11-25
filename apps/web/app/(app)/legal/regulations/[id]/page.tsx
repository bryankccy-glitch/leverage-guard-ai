import { Suspense } from "react";
import { LoadingBlock } from "@/components/ui";
import { RegulationById } from "@/features/legal/routes";

export default function Page() {
  return (
    <>
      <Suspense fallback={<LoadingBlock rows={6} />}><RegulationById /></Suspense>
    </>
  );
}
