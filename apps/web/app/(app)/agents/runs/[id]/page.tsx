import { Suspense } from "react";
import { LoadingBlock } from "@/components/ui";
import { AgentRunById } from "@/features/agents/routes";

export default function Page() {
  return (
    <>
      <Suspense fallback={<LoadingBlock rows={6} />}><AgentRunById /></Suspense>
    </>
  );
}
