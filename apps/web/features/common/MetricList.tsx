"use client";

import { ChevronDown, Sigma } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";
import { useIsEn } from "@/lib/i18n";
import { Badge } from "@/components/ui";
import { cn, fmtValue } from "@/lib/format";
import type { Metric } from "./types";

/** 計算結果：每個數字都可以展開看公式、輸入、規則與是否為簡化估算。 */
export function MetricList({ metrics, keys, highlight }: { metrics: Record<string, Metric>; keys?: string[]; highlight?: string[] }) {
  const list = (keys ?? Object.keys(metrics)).map((k) => metrics[k]).filter(Boolean);
  return (
    <ul className="divide-y divide-line">
      {list.map((m) => (
        <MetricRow key={m.key} m={m} emphasize={highlight?.includes(m.key)} />
      ))}
    </ul>
  );
}

function MetricRow({ m, emphasize }: { m: Metric; emphasize?: boolean }) {
  const isEn = useIsEn();
  const t = useTranslations();
  const locale = useLocale();
  const [open, setOpen] = useState(false);
  const label = t.has(`metrics.${m.key}`) ? t(`metrics.${m.key}`) : m.label;
  const negative = m.value !== null && m.unit === "TWD" && m.value.startsWith("-");
  return (
    <li>
      <button onClick={() => setOpen(!open)} aria-expanded={open} className="flex w-full items-center gap-3 px-1 py-2.5 text-left hover:bg-surface-muted/60">
        <span className="flex-1 text-[14px] text-ink-2">
          {label}
          {m.simplified ? <span className="ml-1.5 align-middle"><Badge tone="unknown">{t("common.simplified")}</Badge></span> : null}
        </span>
        <span className={cn("num text-[15px] font-semibold", emphasize ? "text-[17px]" : "", negative ? "text-critical" : "text-ink")}>
          {negative ? "−" : ""}
          {fmtValue(negative ? m.value!.slice(1) : m.value, m.unit, locale)}
        </span>
        <ChevronDown size={14} className={cn("text-ink-3 transition-transform", open && "rotate-180")} aria-hidden />
      </button>
      {open ? (
        <div className="mb-2 space-y-1.5 rounded-[8px] bg-surface-muted px-3 py-2 text-[12px] text-ink-2">
          <p className="flex items-start gap-1.5"><Sigma size={13} className="mt-0.5 shrink-0" aria-hidden /><span><b>{t("common.formula")}{isEn ? ": " : "："}</b>{m.formula}</span></p>
          {Object.keys(m.inputs).length ? (
            <p className="num">{Object.entries(m.inputs).filter(([, v]) => v !== null && v !== "None").map(([k, v]) => `${k}=${v}`).join("　")}</p>
          ) : null}
          {m.rule_ids.length ? <p>{t("common.ruleVersion")}{isEn ? ": " : "："}{m.rule_ids.join(isEn ? ", " : "、")}</p> : null}
          {m.note ? <p className="text-ink-3">※ {m.note}</p> : null}
        </div>
      ) : null}
    </li>
  );
}
