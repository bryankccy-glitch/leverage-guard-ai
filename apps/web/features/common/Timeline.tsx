"use client";

import { motion } from "motion/react";
import { BadgeCheck, CalendarClock, ChevronDown, ExternalLink, FileWarning, ShieldQuestion } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";
import { Badge, EventStatus } from "@/components/ui";
import { cn, fmtDate, fmtNum } from "@/lib/format";
import type { Citation, TimelineNode } from "./types";

const NEUTRAL = new Set(["position_opened", "price_change", "trade_executed", "top_up_paid", "offset_reported"]);

const DOT: Record<string, string> = {
  triggered_in_simulation: "bg-critical",
  requires_confirmation: "bg-warning",
  potential: "bg-high",
  resolved: "bg-normal",
  not_triggered: "bg-unknown",
};

export function Timeline({ nodes, upTo, compact }: { nodes: TimelineNode[]; upTo?: number; compact?: boolean }) {
  const shown = upTo === undefined ? nodes : nodes.filter((n) => n.step <= upTo);
  const items = compact ? shown.filter((n) => n.event_type !== "price_change") : shown;
  return (
    <ol className="relative space-y-3 before:absolute before:bottom-2 before:left-[11px] before:top-2 before:w-px before:bg-line" aria-label="法律責任時間軸">
      {items.map((n, i) => (
        <motion.li key={n.id} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.2, delay: Math.min(i * 0.03, 0.3) }} className="relative pl-8">
          <span aria-hidden className={cn("absolute left-[6px] top-3 h-3 w-3 rounded-full ring-4 ring-surface", NEUTRAL.has(n.event_type) ? "bg-blue" : (DOT[n.status] ?? "bg-unknown"))} />
          <TimelineCard n={n} />
        </motion.li>
      ))}
    </ol>
  );
}

function TimelineCard({ n }: { n: TimelineNode }) {
  const t = useTranslations("timeline");
  const tc = useTranslations("common");
  const locale = useLocale();
  const [open, setOpen] = useState(n.status === "triggered_in_simulation" && n.event_type !== "price_change");
  const title = locale === "en" ? n.title_en : n.title_zh;
  const isPrice = n.event_type === "price_change";
  return (
    <div className={cn("rounded-[12px] border border-line bg-surface", isPrice && "bg-surface-muted")}>
      <button onClick={() => setOpen(!open)} aria-expanded={open} className="flex w-full flex-wrap items-center gap-2 px-3 py-2.5 text-left">
        <span className="num w-[86px] shrink-0 text-[12px] text-ink-3">{n.date ? fmtDate(n.date, locale) : t("noDate")}</span>
        <span className={cn("min-w-0 flex-1 text-[14px]", isPrice ? "text-ink-2" : "font-semibold text-ink")}>{title}</span>
        {NEUTRAL.has(n.event_type) ? (!isPrice ? <Badge tone="blue">{tc("simulation")}</Badge> : null) : <EventStatus status={n.status} />}
        {n.unreviewed && !isPrice ? <Badge tone="unknown" icon={<ShieldQuestion size={12} aria-hidden />}>{tc("unreviewed")}</Badge> : null}
        {!n.unreviewed && n.ai_checked && !isPrice ? <Badge tone="unknown" icon={<ShieldQuestion size={12} aria-hidden />}>{tc("aiChecked")}</Badge> : null}
        {n.unverified ? <Badge tone="warning" icon={<FileWarning size={12} aria-hidden />}>{tc("unverified")}</Badge> : null}
        <ChevronDown size={14} className={cn("text-ink-3 transition-transform", open && "rotate-180")} aria-hidden />
      </button>
      {open ? (
        <div className="space-y-3 border-t border-line px-3 py-3 text-[13px]">
          <Row label={t("trigger")}>{n.trigger_condition}</Row>
          {Object.keys(n.financial_impact).length ? (
            <Row label={t("impact")}>
              <span className="num flex flex-wrap gap-x-4 gap-y-1">
                {Object.entries(n.financial_impact).map(([k, v]) => (
                  <span key={k}>{k}：<b className="text-ink">{fmtNum(v, locale)}</b></span>
                ))}
              </span>
            </Row>
          ) : null}
          {n.deadline ? (
            <Row label={t("deadline")}>
              <span className="flex items-center gap-1.5"><CalendarClock size={14} aria-hidden /> <b className="num">{fmtDate(n.deadline, locale)}</b>{n.deadline_note ? <span className="text-ink-3">（{n.deadline_note}）</span> : null}</span>
            </Row>
          ) : null}
          {n.plain_language ? <p className="whitespace-pre-line rounded-[8px] bg-brand-soft px-3 py-2 text-ink">{n.plain_language}</p> : null}
          {n.event_type === "margin_call_notice" ? <p className="text-[12px] text-ink-3">※ {t("simulatedNotice")}</p> : null}
          <div className="grid gap-3 md:grid-cols-2">
            <ListBlock label={t("investorRights")} items={n.investor_rights} />
            <ListBlock label={t("investorObligations")} items={n.investor_obligations} />
            <ListBlock label={t("brokerRights")} items={n.broker_rights} />
            <ListBlock label={t("brokerObligations")} items={n.broker_obligations} />
          </div>
          <ListBlock label={t("evidence")} items={n.required_evidence} />
          {n.legal_basis.length ? (
            <div>
              <p className="mb-1 font-semibold text-ink-2">{t("legalBasis")}</p>
              <ul className="space-y-1.5">{n.legal_basis.map((c, i) => <CitationItem key={i} c={c} />)}</ul>
            </div>
          ) : null}
          <ListBlock label={t("uncertainty")} items={n.uncertainty} tone="warning" />
        </div>
      ) : null}
    </div>
  );
}

export function CitationItem({ c }: { c: Citation }) {
  const t = useTranslations("timeline");
  return (
    <li className="rounded-[8px] border border-line px-3 py-2">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-medium text-ink">{c.official_title} {c.article_number}</span>
        <Badge tone={c.validated ? "normal" : "critical"} icon={<BadgeCheck size={12} aria-hidden />}>{c.validated ? t("quoteValidated") : t("quoteFailed")}</Badge>
        <span className="num text-[11px] text-ink-3">v{c.version}</span>
        <a href={c.official_url} target="_blank" rel="noopener noreferrer" className="ml-auto inline-flex items-center gap-1 text-[12px] text-blue hover:underline">
          {c.authority} <ExternalLink size={11} aria-hidden />
        </a>
      </div>
      <blockquote className="mt-1 border-l-2 border-brand pl-2 text-[12.5px] text-ink-2">「{c.quote}」</blockquote>
    </li>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="grid gap-1 md:grid-cols-[110px_1fr]">
      <span className="font-semibold text-ink-2">{label}</span>
      <span className="text-ink">{children}</span>
    </div>
  );
}

function ListBlock({ label, items, tone }: { label: string; items: string[]; tone?: "warning" }) {
  if (!items.length) return null;
  return (
    <div>
      <p className={cn("mb-1 font-semibold", tone === "warning" ? "text-warning" : "text-ink-2")}>{label}</p>
      <ul className="list-disc space-y-0.5 pl-5 text-ink-2">{items.map((x, i) => <li key={i}>{x}</li>)}</ul>
    </div>
  );
}
