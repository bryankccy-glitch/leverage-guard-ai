import { Suspense } from "react";
import { LoadingBlock } from "@/components/ui";
import { ScenarioDetailById } from "@/features/scenarios/routes";

export default function Page() {
  return (
    <Suspense fallback={<LoadingBlock rows={6} />}>
      <ScenarioDetailById />
    </Suspense>
  );
}
