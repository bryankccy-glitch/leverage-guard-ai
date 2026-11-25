"use client";

import { ArrowUpRight, Layers, TrendingDown, TrendingUp, Zap } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { Badge, PageHeader } from "@/components/ui";

export function SimulatorIndex() {
  const t = useTranslations();
  const items = [
    { href: "/simulator/margin", title: t("nav.margin"), desc: "維持率、追繳門檻、補繳差額、剩餘債務", icon: <TrendingDown size={20} />, badge: "P0" },
    { href: "/simulator/day-trading", title: t("nav.dayTrading"), desc: "完成／未完成沖銷、交割資金缺口、強制買回", icon: <Zap size={20} />, badge: "P0" },
    { href: "/simulator/portfolio", title: "整戶維持率試算", desc: "多個融資部位合併計算（不是各部位平均）", icon: <Layers size={20} />, badge: "P1" },
    { href: "/simulator/short-selling", title: "融券模擬", desc: "第二階段功能", icon: <TrendingUp size={20} />, badge: "P2" },
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
