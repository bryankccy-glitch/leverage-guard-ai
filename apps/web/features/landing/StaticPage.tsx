"use client";

import type { ReactNode } from "react";
import { useIsEn } from "@/lib/i18n";
import { PublicFooter, PublicNav } from "./PublicChrome";

export function StaticPage({ title, titleEn, lead, leadEn, children }: { title: string; titleEn: string; lead?: string; leadEn?: string; children: ReactNode }) {
  const isEn = useIsEn();
  const shownTitle = isEn ? titleEn : title;
  const shownLead = isEn ? leadEn : lead;
  return (
    <div className="min-h-screen bg-bg">
      <PublicNav />
      <main id="main" className="mx-auto max-w-3xl px-5 py-12">
        <h1 className="text-[32px] font-bold tracking-tight text-ink">{shownTitle}</h1>
        {shownLead ? <p className="mt-3 text-[16px] text-ink-2">{shownLead}</p> : null}
        <div className="prose-lg mt-8 space-y-6 text-[15px] leading-7 text-ink-2 [&_h2]:mt-8 [&_h2]:text-[20px] [&_h2]:font-semibold [&_h2]:text-ink [&_li]:ml-5 [&_li]:list-disc [&_a]:text-blue [&_a]:underline">
          {children}
        </div>
      </main>
      <PublicFooter />
    </div>
  );
}
