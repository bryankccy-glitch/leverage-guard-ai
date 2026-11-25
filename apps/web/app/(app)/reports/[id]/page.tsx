import { Suspense } from "react";
import { LoadingBlock } from "@/components/ui";
import { ReportById } from "@/features/reports/routes";

export default function Page() {
  return (
    <>
      <Suspense fallback={<LoadingBlock rows={6} />}><ReportById /></Suspense>
    </>
  );
}
