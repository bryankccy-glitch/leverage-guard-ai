"use client";

import { ArrowUpRight, Layers, TrendingDown, TrendingUp } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { useL } from "@/lib/i18n";
import { Badge, PageHeader } from "@/components/ui";

export function SimulatorIndex() {
  const t = useTranslations();
  const L = useL();
  const items = [
    { href: "/simulator/margin", title: t("nav.margin"), desc: L("維持率、追繳門檻、補繳差額、剩餘債務", "Maintenance ratio, call threshold, top-up amount, residual debt"), icon: <TrendingDown size={20} />, badge: "P0" },
    { href: "/simulator/portfolio", title: L("整戶維持率試算", "Account-level maintenance ratio"), desc: L("多個融資部位合併計算（不是各部位平均）", "Combines multiple margin positions (not an average of positions)"), icon: <Layers size={20} />, badge: "P1" },
    { href: "/simulator/short-selling", title: L("融券模擬", "Short selling simulation"), desc: L("第二階段功能", "Phase-two feature"), icon: <TrendingUp size={20} />, badge: "P2" },
  ];
  return (
    <>
      <PageHeader title={t("nav.simulation")} subtitle={t("common.notAdvice")} />
      <div className="grid gap-4 md:grid-cols-2">
        {items.map((i) => (
          <Link key={i.href} href={i.href} className="flex gap-4 rounded-[12px] border border-line bg-surface p-5 shadow-card hover:border-brand">
            <span className="grid h-11 w-11 shrink-0 place-items-center rounded-[10px] bg-brand-soft text-brand">{i.icon}</span>
            <span className="flex-1">
              <span className="flex items-center gap-2 font-semibold text-ink">{i.title}<Badge tone={i.badge === "P2" ? "unknown" : "blue"}>{i.badge}</Badge></span>
              <span className="mt-1 block text-[13px] text-ink-2">{i.desc}</span>
            </span>
            <ArrowUpRight size={16} className="text-ink-3" />
          </Link>
        ))}
      </div>
    </>
  );
}
