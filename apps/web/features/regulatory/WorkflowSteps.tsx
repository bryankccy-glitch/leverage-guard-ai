"use client";

import { useL } from "@/lib/i18n";
const STEPS = ["Fetch", "Validate", "Detect Changes", "Compare Versions", "Classify Impact", "Draft Rule", "Human Review", "Publish", "Notify"];

export function WorkflowSteps() {
  const L = useL();
  return (
    <ol className="flex flex-wrap items-center gap-2 text-[12px]" aria-label={L("法規監察流程", "Regulatory monitoring workflow")}>
      {STEPS.map((s, i) => (
        <li key={s} className="flex items-center gap-2">
          <span className={i === 6 ? "rounded-full bg-warning-soft px-3 py-1 font-semibold text-warning" : "rounded-full border border-line bg-surface px-3 py-1 text-ink-2"}>{s}</span>
          {i < STEPS.length - 1 ? <span className="text-ink-3" aria-hidden>→</span> : null}
        </li>
      ))}
    </ol>
  );
}
