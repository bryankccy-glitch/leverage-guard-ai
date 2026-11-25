import { Suspense } from "react";
import { AppShell } from "@/components/shell/AppShell";

function ShellFallback() {
  return (
    <div className="flex min-h-screen gap-3 bg-bg p-3" aria-busy="true">
      <div className="hidden w-[248px] rounded-[16px] border border-line bg-surface md:block" />
      <div className="flex-1 space-y-4">
        <div className="h-[62px] rounded-[16px] border border-line bg-surface" />
        <div className="skeleton h-40 rounded-[16px]" />
      </div>
    </div>
  );
}

export default function AppLayout({ children }: LayoutProps<"/">) {
  return (
    <Suspense fallback={<ShellFallback />}>
      <AppShell>{children}</AppShell>
    </Suspense>
  );
}
