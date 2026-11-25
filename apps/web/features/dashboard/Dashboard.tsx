"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowUpRight, BookOpenText, ChevronDown, CircleHelp, FileSearch, FileText, FlaskConical, Radar, RefreshCw, Scale, TrendingDown, Zap } from "lucide-react";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { useState, type ReactNode } from "react";
import { useRuleVersion } from "@/components/shell/AppShell";
import { Badge, Card, EmptyState, ErrorState, EventStatus, LoadingBlock, SimBadge } from "@/components/ui";
import { api } from "@/lib/api";
import { cn, fmtDate, fmtMoney, fmtNum } from "@/lib/format";
import { useAuth, useHydrated } from "@/stores/auth";

type Dash = {
  kpis: { scenarios: number; contracts: number; reports: number; reg_updates: number; unread: number; pending_legal_items: number };
  recent_simulations: { id: string; scenario_name: string; scenario_type: string; status: string; rule_version_label: string | null; is_demo: boolean; created_at: string }[];
  risk_overview: { event_type: string; event_status: string; trigger_condition: string; scenario_name: string; scenario_id: string }[];
  regulatory_updates: { id: string; title: string; authority: string; review_status: string; is_demo: boolean; effective_date: string | null; detected_at: string }[];
  account: null | { id: string; name: string; financial_state: { market_value: string; borrowed: string; own_equity: string; unrealized_pnl: string; account_ratio: null | Record<string, { value: string }> } };
};

export function Dashboard() {
  const t = useTranslations();
  const locale = useLocale();
  const token = useAuth((s) => s.token);
  const hydrated = useHydrated();
  const rv = useRuleVersion().data;
  const q = useQuery({ queryKey: ["dashboard", token], queryFn: () => api<Dash>("/dashboard"), enabled: !!token });
  const [expand, setExpand] = useState(false);
  const d = q.data;

  return (
    <div className="space-y-4">
      {/* 標題列：參考版面（左標題、右側更新時間／規則版本／匯出） */}
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h1 className="text-[28px] font-bold leading-tight tracking-tight text-ink md:text-[32px]">{t("dashboard.title")}</h1>
          <p className="text-[14px] text-ink-2">{t("dashboard.subtitle")}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button onClick={() => q.refetch()} className="flex h-11 items-center gap-3 rounded-full border border-line bg-surface pl-4 pr-1.5 text-[14px] text-ink shadow-card">
            {t("dashboard.updated")} {hydrated && q.dataUpdatedAt ? new Intl.DateTimeFormat(locale, { hour: "2-digit", minute: "2-digit", timeZone: "Asia/Taipei" }).format(q.dataUpdatedAt) : "—"}
            <span className="grid h-8 w-8 place-items-center rounded-full bg-ink text-bg"><RefreshCw size={14} className={q.isFetching ? "animate-spin" : ""} aria-hidden /></span>
          </button>
          <span className="flex h-11 items-center gap-2 rounded-full border border-line bg-surface px-4 text-[14px] text-ink shadow-card">
            {t("common.ruleVersion")} <span className="num font-medium">{hydrated ? (rv?.rule_version ?? "—") : "—"}</span>
          </span>
          <Link href="/reports" className="flex h-11 items-center gap-3 rounded-full bg-ink pl-5 pr-1.5 text-[14px] font-medium text-bg">
            {t("common.export")}
            <span className="grid h-8 w-8 place-items-center rounded-full bg-bg text-ink"><ArrowUpRight size={15} aria-hidden /></span>
          </Link>
        </div>
      </div>

      {!hydrated ? <Card><LoadingBlock rows={4} /></Card> : !token ? (
        <Card><EmptyState title={t("dashboard.guestTitle")} desc={t("dashboard.loginPrompt")} action={<Link href="/login" className="text-blue underline">{t("shell.login")}</Link>} /></Card>
      ) : q.isLoading ? <Card><LoadingBlock rows={6} /></Card> : q.error ? <Card><ErrorState error={q.error} onRetry={() => q.refetch()} /></Card> : d ? (
        <>
          {/* KPI 四卡：第一張為主卡 */}
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <KpiCard hero label={t("dashboard.kpiPending")} value={String(d.kpis.pending_legal_items)} sub={t("timeline.status.requires_confirmation")} icon={<CircleHelp size={18} />} href="/legal/rights" />
            <KpiCard label={t("dashboard.kpiScenarios")} value={String(d.kpis.scenarios)} sub={t("common.simulation")} icon={<FlaskConical size={18} />} tone="bg-high" valueTone="text-high" href="/scenarios" />
            <KpiCard label={t("dashboard.kpiContracts")} value={String(d.kpis.contracts)} sub={t("nav.contracts")} icon={<FileSearch size={18} />} tone="bg-blue" valueTone="text-blue" href="/contracts" />
            <KpiCard label={t("dashboard.kpiUpdates")} value={String(d.kpis.reg_updates)} sub={`${t("dashboard.kpiReports")} ${d.kpis.reports}`} icon={<Radar size={18} />} tone="bg-normal" valueTone="text-normal" href="/regulatory-monitor" />
          </div>

          {/* 次要指標：模擬帳戶 */}
          <div className="grid gap-4 md:grid-cols-3">
            <MiniStat icon={<TrendingDown size={22} />} label={t("dashboard.accountValue")} value={d.account ? fmtMoney(d.account.financial_state.market_value, locale) : "—"} badge />
            <MiniStat icon={<Scale size={22} />} label={t("dashboard.accountBorrowed")} value={d.account ? fmtMoney(d.account.financial_state.borrowed, locale) : "—"} badge />
            <MiniStat icon={<CircleHelp size={22} />} label={t("dashboard.accountRatio")} value={d.account?.financial_state.account_ratio ? `${fmtNum(d.account.financial_state.account_ratio.account_maintenance_ratio.value, locale, 2)}%` : "—"} badge />
          </div>

          {/* 主內容兩欄 */}
          <div className="grid gap-4 xl:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
            <Card className="p-5">
              <h2 className="text-[18px] font-semibold text-ink">{t("dashboard.riskOverview")}</h2>
              <p className="text-[13px] text-ink-3">{t("dashboard.riskOverviewDesc")}</p>
              <RiskBars items={d.risk_overview} />
            </Card>
            <Card className="p-5">
              <div className="flex items-start justify-between">
                <div>
                  <h2 className="text-[18px] font-semibold text-ink">{t("dashboard.regUpdates")}</h2>
                  <p className="text-[13px] text-ink-3">{t("regulatory.subtitle").slice(0, 26)}…</p>
                </div>
                <Badge tone="blue">{d.regulatory_updates.length} total</Badge>
              </div>
              <ul className="mt-4 space-y-3">
                {d.regulatory_updates.length === 0 ? <li className="text-[13px] text-ink-3">{t("regulatory.noUpdates")}</li> : d.regulatory_updates.map((u) => (
                  <li key={u.id}>
                    <Link href={`/regulatory-monitor/updates?id=${u.id}`} className="flex items-center gap-3 rounded-[10px] p-1 hover:bg-surface-muted">
                      <span className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-surface-muted text-brand"><Radar size={18} aria-hidden /></span>
                      <span className="min-w-0 flex-1">
                        <span className="line-clamp-2 text-[14px] text-ink">{u.title}</span>
                        <span className="mt-0.5 flex gap-1.5">
                          {u.is_demo ? <Badge tone="warning">{t("regulatory.demoBadge")}</Badge> : <Badge tone="blue">{t("regulatory.realBadge")}</Badge>}
                          <Badge tone="unknown">{t(`regulatory.reviewStatus.${u.review_status}`)}</Badge>
                        </span>
                      </span>
                    </Link>
                  </li>
                ))}
              </ul>
            </Card>
          </div>

          {/* 底部區段 */}
          <div className="flex items-center justify-between pt-2">
            <h2 className="text-[18px] font-semibold text-ink">{t("dashboard.recent")}</h2>
            <button onClick={() => setExpand(!expand)} aria-expanded={expand} className="flex items-center gap-1 text-[14px] text-ink">
              {t("common.details")} <ChevronDown size={16} className={cn("transition-transform", expand && "rotate-180")} />
            </button>
          </div>
          <div className="grid gap-4 md:grid-cols-3">
            {(expand ? d.recent_simulations : d.recent_simulations.slice(0, 3)).map((s) => (
              <Link key={s.id} href={`/scenarios/${s.id}`} className="rounded-[12px] border border-line bg-surface p-5 shadow-card hover:border-brand">
                <p className="text-[13px] text-ink-3">{s.scenario_type === "day_trading" ? t("nav.dayTrading") : t("nav.margin")}</p>
                <p className="mt-1 line-clamp-2 text-[16px] font-semibold text-ink">{s.scenario_name}</p>
                <p className="num mt-2 text-[12px] text-ink-3">{fmtDate(s.created_at, locale, true)} · {s.rule_version_label ?? "—"}</p>
                <div className="mt-2 flex gap-1.5">{s.is_demo ? <Badge tone="warning">{t("common.demo")}</Badge> : null}<SimBadge /></div>
              </Link>
            ))}
            {d.recent_simulations.length === 0 ? <Card className="md:col-span-3"><EmptyState title={t("common.empty")} /></Card> : null}
          </div>
        </>
      ) : null}

      {/* 快速開始（訪客也可用） */}
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <QuickAction href="/simulator/margin" icon={<TrendingDown size={18} />} label={t("dashboard.qaMargin")} />
        <QuickAction href="/simulator/day-trading" icon={<Zap size={18} />} label={t("dashboard.qaDayTrade")} />
        <QuickAction href="/contracts/upload" icon={<FileText size={18} />} label={t("dashboard.qaContract")} />
        <QuickAction href="/scenarios/new" icon={<FlaskConical size={18} />} label={t("dashboard.qaLab")} />
      </div>
      <Card className="p-5">
        <h2 className="flex items-center gap-2 text-[16px] font-semibold text-ink"><BookOpenText size={18} className="text-brand" />{t("dashboard.knowledge")}</h2>
        <div className="mt-3 grid gap-3 md:grid-cols-3">
          <KnowledgeLink href="/legal/search?q=追繳" title="追繳與擔保維持率" desc="證交所融資融券業務操作辦法第 53、54 條" />
          <KnowledgeLink href="/legal/search?q=處分其擔保品" title="擔保品處分與剩餘債務" desc="第 55、81 條：處分、溢額發還、不足補足" />
          <KnowledgeLink href="/legal/search?q=當日沖銷" title="現股當沖與強制買回" desc="當日沖銷交易作業辦法第 1、7、9、13 條" />
        </div>
      </Card>
    </div>
  );
}

function KpiCard({ label, value, sub, icon, hero, tone, valueTone, href }: { label: string; value: string; sub: string; icon: ReactNode; hero?: boolean; tone?: string; valueTone?: string; href: string }) {
  const t = useTranslations("common");
  return (
    <div className={cn("rounded-[16px] p-5", hero ? "bg-hero text-hero-fg" : "border border-line bg-surface shadow-card")}>
      <div className="flex items-start justify-between">
        <p className={cn("text-[15px]", hero ? "" : "text-ink")}>{label}</p>
        <span className={cn("grid h-11 w-11 place-items-center rounded-full", hero ? "bg-black/25 text-current" : `${tone} text-white`)}>{icon}</span>
      </div>
      <p className={cn("num mt-3 text-[36px] font-bold leading-none", hero ? "" : valueTone)}>{value}</p>
      <div className="mt-3 flex items-center justify-between text-[13px]">
        <span className={hero ? "opacity-85" : "text-ink-3"}>{sub}</span>
        <Link href={href} className={cn("flex items-center gap-1", hero ? "" : "text-ink")}>{t("details")} <ChevronDown size={14} className="-rotate-90" /></Link>
      </div>
    </div>
  );
}

function MiniStat({ icon, label, value, badge }: { icon: ReactNode; label: string; value: string; badge?: boolean }) {
  return (
    <div className="flex items-center gap-4 rounded-[16px] border border-line bg-surface p-5 shadow-card">
      <span className="grid h-12 w-12 place-items-center rounded-full bg-surface-muted text-ink-2">{icon}</span>
      <div className="min-w-0">
        <p className="flex items-center gap-2 text-[13px] text-ink-3">{label}{badge ? <SimBadge /> : null}</p>
        <p className="num text-[26px] font-bold text-ink">{value}</p>
      </div>
    </div>
  );
}

function RiskBars({ items }: { items: Dash["risk_overview"] }) {
  const t = useTranslations();
  const counts = {
    triggered_in_simulation: items.filter((i) => i.event_status === "triggered_in_simulation" && i.event_type !== "price_change").length,
    requires_confirmation: items.filter((i) => i.event_status === "requires_confirmation").length,
    scenarios: new Set(items.map((i) => i.scenario_id)).size,
  };
  const max = Math.max(1, counts.triggered_in_simulation, counts.requires_confirmation, counts.scenarios);
  const bars = [
    { key: "triggered_in_simulation", label: t("timeline.status.triggered_in_simulation"), value: counts.triggered_in_simulation, color: "var(--chart-2)" },
    { key: "requires_confirmation", label: t("timeline.status.requires_confirmation"), value: counts.requires_confirmation, color: "var(--chart-1)" },
    { key: "scenarios", label: t("dashboard.kpiScenarios"), value: counts.scenarios, color: "var(--chart-3)" },
  ];
  const list = items.filter((i) => i.event_type !== "price_change").slice(0, 5);
  return (
    <div className="mt-4 grid gap-6 md:grid-cols-[220px_1fr]">
      <div className="flex h-48 items-end gap-4" role="img" aria-label={bars.map((b) => `${b.label} ${b.value}`).join("，")}>
        {bars.map((b) => (
          <div key={b.key} className="flex h-full w-14 items-end rounded-full bg-surface-muted dark:bg-black">
            <div className="w-full rounded-full transition-[height] duration-300" style={{ height: `${Math.max(14, (b.value / max) * 100)}%`, background: b.color }} />
          </div>
        ))}
      </div>
      <ul className="space-y-3">
        {bars.map((b) => (
          <li key={b.key} className="flex items-center gap-3">
            <span className="h-3 w-3 rounded-full" style={{ background: b.color }} aria-hidden />
            <span className="flex-1 text-[15px] text-ink">{b.label}</span>
            <span className="num text-[16px] font-semibold text-ink">{b.value}</span>
          </li>
        ))}
        <li className="border-t border-line pt-2">
          <ul className="space-y-1.5">
            {list.map((i, n) => (
              <li key={n} className="flex items-center gap-2 text-[13px]">
                <EventStatus status={i.event_status} />
                <Link href={`/scenarios/${i.scenario_id}`} className="truncate text-ink-2 hover:text-ink">{i.scenario_name}</Link>
              </li>
            ))}
          </ul>
        </li>
      </ul>
    </div>
  );
}

function QuickAction({ href, icon, label }: { href: string; icon: ReactNode; label: string }) {
  return (
    <Link href={href} className="flex items-center gap-3 rounded-[12px] border border-line bg-surface px-4 py-3 text-[14px] font-medium text-ink shadow-card hover:border-brand">
      <span className="grid h-9 w-9 place-items-center rounded-full bg-brand-soft text-brand">{icon}</span>
      {label}
      <ArrowUpRight size={15} className="ml-auto text-ink-3" />
    </Link>
  );
}

function KnowledgeLink({ href, title, desc }: { href: string; title: string; desc: string }) {
  return (
    <Link href={href} className="rounded-[12px] border border-line p-4 hover:border-brand">
      <p className="font-medium text-ink">{title}</p>
      <p className="mt-1 text-[12.5px] text-ink-3">{desc}</p>
    </Link>
  );
}
