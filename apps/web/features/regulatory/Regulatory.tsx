"use client";

import { useQuery } from "@tanstack/react-query";
import { ExternalLink, Radar } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { useL, useIsEn } from "@/lib/i18n";
import { Badge, Card, CardHeader, EmptyState, ErrorState, LoadingBlock, Notice } from "@/components/ui";
import { api } from "@/lib/api";
import { cn, fmtDate } from "@/lib/format";
import { WorkflowSteps } from "./WorkflowSteps";

type Update = { id: string; title: string; authority: string; official_url: string | null; change_summary: string; affected_trading_types: string[]; is_demo: boolean; review_status: string; publication_date: string | null; effective_date: string | null; detected_at: string };
type UpdateDetail = Update & { changed_articles: { article_number: string }[]; diff: ({ type: "added" | "removed"; text: string } | { article_number: string; change: string; ops: { op: string; removed: string; added: string }[] })[]; impact_analysis: Record<string, unknown>; draft_rule_version_id: string | null };

export function RegulatoryHome() {
  const t = useTranslations("regulatory");
  const locale = useLocale();
  const q = useQuery({ queryKey: ["reg-updates"], queryFn: () => api<{ items: Update[] }>("/regulatory/updates", { auth: false }) });
  return (
    <div className="space-y-5">
      <WorkflowSteps />
      <Card>
        <CardHeader title={t("updates")} />
        {q.isLoading ? <LoadingBlock /> : q.error ? <ErrorState error={q.error} /> : q.data!.items.length === 0 ? <EmptyState icon={<Radar size={28} />} title={t("noUpdates")} /> : (
          <ul className="divide-y divide-line px-5">
            {q.data!.items.map((u) => (
              <li key={u.id} className="flex flex-wrap items-center gap-3 py-3">
                <Link href={`/regulatory-monitor/updates?id=${u.id}`} className="min-w-0 flex-1 font-medium text-ink hover:text-brand">{u.title}</Link>
                {u.is_demo ? <Badge tone="warning">{t("demoBadge")}</Badge> : <Badge tone="blue">{t("realBadge")}</Badge>}
                <Badge tone="unknown">{t(`reviewStatus.${u.review_status}`)}</Badge>
                <span className="num text-[12px] text-ink-3">{fmtDate(u.detected_at, locale)}</span>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}

export function UpdateDetailView() {
  const isEn = useIsEn();
  const t = useTranslations("regulatory");
  const L = useL();
  const locale = useLocale();
  const id = useSearchParams().get("id");
  const list = useQuery({ queryKey: ["reg-updates"], queryFn: () => api<{ items: Update[] }>("/regulatory/updates", { auth: false }) });
  const chosen = id ?? list.data?.items[0]?.id;
  const q = useQuery({ queryKey: ["reg-update", chosen], queryFn: () => api<UpdateDetail>(`/regulatory/updates/${chosen}`, { auth: false }), enabled: !!chosen });
  const impact = useQuery({ queryKey: ["reg-impact", chosen], queryFn: () => api<{ comparison: null | { scenario: string; old: { rule_version: string; threshold: string; events: { date: string | null; title: string; status: string }[] }; new: { rule_version: string; threshold: string; events: { date: string | null; title: string; status: string }[] } }; note: string }>(`/regulatory/updates/${chosen}/impact`, { auth: false }), enabled: !!chosen });
  if (list.isLoading || q.isLoading) return <Card><LoadingBlock rows={6} /></Card>;
  if (!chosen) return <Card><EmptyState title={t("noUpdates")} /></Card>;
  if (q.error) return <Card><ErrorState error={q.error} /></Card>;
  const u = q.data!;
  return (
    <div className="space-y-5">
      <Card className="p-5">
        <div className="flex flex-wrap items-center gap-2">
          {u.is_demo ? <Badge tone="warning">{t("demoBadge")}</Badge> : <Badge tone="blue">{t("realBadge")}</Badge>}
          <Badge tone="unknown">{t("review")}{isEn ? ": " : "："}{t(`reviewStatus.${u.review_status}`)}</Badge>
          <span className="num text-[12px] text-ink-3">{L("偵測", "Detected")} {fmtDate(u.detected_at, locale, true)} · {L("生效", "Effective")} {u.effective_date ?? "—"}</span>
        </div>
        <h2 className="mt-2 text-[20px] font-semibold text-ink">{u.title}</h2>
        <p className="mt-1 text-[14px] text-ink-2">{u.change_summary}</p>
        <p className="mt-1 text-[13px] text-ink-3">{u.authority} · {t("affected")}{isEn ? ": " : "："}{u.affected_trading_types.join(isEn ? ", " : "、") || "—"}</p>
        {u.official_url ? <a href={u.official_url} target="_blank" rel="noopener noreferrer" className="mt-1 inline-flex items-center gap-1 text-[13px] text-blue hover:underline">{L("官方來源", "Official source")} <ExternalLink size={12} /></a> : null}
      </Card>
      <Card>
        <CardHeader title={t("diff")} />
        <div className="space-y-2 p-5 text-[14px]">
          {u.diff.map((d, i) =>
            "type" in d ? (
              <p key={i} className={cn("rounded-[8px] px-3 py-2", d.type === "added" ? "bg-normal-soft text-normal" : "bg-critical-soft text-critical line-through")}>
                <span className="mr-2 text-[12px] font-semibold no-underline">{d.type === "added" ? t("added") : t("removed")}</span><span lang="zh-Hant-TW">{d.text}</span>
              </p>
            ) : (
              <div key={i} className="rounded-[8px] border border-line p-3">
                <p className="font-semibold text-ink">{d.article_number}{isEn ? ` (${d.change})` : `（${d.change}）`}</p>
                {d.ops.map((o, j) => (
                  <p key={j} className="mt-1 text-[13px]">
                    {o.removed ? <span lang="zh-Hant-TW" className="mr-1 rounded bg-critical-soft px-1 text-critical line-through">{o.removed}</span> : null}
                    {o.added ? <span lang="zh-Hant-TW" className="rounded bg-normal-soft px-1 text-normal">{o.added}</span> : null}
                  </p>
                ))}
              </div>
            ),
          )}
        </div>
      </Card>
      <Card>
        <CardHeader title={t("impact")} desc={impact.data?.note} />
        {impact.isLoading ? <LoadingBlock /> : impact.data?.comparison ? (
          <div className="grid gap-4 p-5 md:grid-cols-2">
            <p className="text-[13px] text-ink-2 md:col-span-2">{impact.data.comparison.scenario}</p>
            {(["old", "new"] as const).map((k) => {
              const c = impact.data!.comparison![k];
              return (
                <div key={k} className={cn("rounded-[12px] border p-4", k === "new" ? "border-warning" : "border-line")}>
                  <p className="font-semibold text-ink">{k === "old" ? t("oldRule") : t("newRule")}{L("：門檻 ", ": threshold ")}{Number(c.threshold) * 100}%</p>
                  <p className="num text-[11px] text-ink-3">{c.rule_version}</p>
                  <ul className="mt-2 space-y-1 text-[13px]">
                    {c.events.map((e, i) => <li key={i} className="flex justify-between gap-2"><span>{e.title}</span><span className="num text-ink-3">{e.date ?? "—"}</span></li>)}
                  </ul>
                </div>
              );
            })}
          </div>
        ) : <p className="p-5 text-[13px] text-ink-3">{impact.data?.note ?? "—"}</p>}
      </Card>
      <Notice tone="blue">{L("AI 偵測到法規變動後只會建立草案規則；必須由法律審查員確認、測試並核准新版本，才會套用到計算。示範更新永遠不會套用到正式計算。", "When AI detects a regulatory change it only creates a draft rule; a legal reviewer must confirm, test and approve the new version before it is used in calculations. Demo updates are never applied to real calculations.")}</Notice>
    </div>
  );
}
