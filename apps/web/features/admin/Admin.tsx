"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Activity, BookOpenText, Bot, ClipboardCheck, Database, FileClock, FlaskConical, Layers3, ListChecks, ScrollText, Users } from "lucide-react";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { useState, type ReactNode } from "react";
import { Badge, Button, Card, CardHeader, EmptyState, ErrorState, Input, LoadingBlock, Notice, SuccessNote } from "@/components/ui";
import { api } from "@/lib/api";
import { fmtDate } from "@/lib/format";
import { useAuth } from "@/stores/auth";
import { CitationItem } from "../common/Timeline";
import type { Citation } from "../common/types";
import { DocList } from "../legal/Legal";

function useAdminGuard(roles: string[] = ["legal_reviewer", "system_admin"]) {
  const user = useAuth((s) => s.user);
  return !!user && roles.includes(user.role);
}

function Guard({ roles, children }: { roles?: string[]; children: ReactNode }) {
  const t = useTranslations("admin");
  const ok = useAdminGuard(roles);
  if (!ok) return <Card><EmptyState title={t("onlyReviewer")} desc="權限由後端與資料庫 RLS 強制執行；這裡只是提示。" action={<Link href="/login" className="text-blue underline">切換帳號</Link>} /></Card>;
  return <>{children}</>;
}

export function AdminHome() {
  const t = useTranslations("admin");
  const items: [string, string, ReactNode, string][] = [
    ["/admin/review-queue", t("reviewQueue"), <ClipboardCheck key="i" size={20} />, "核准、啟用或退回規則版本與法規更新"],
    ["/admin/legal-rules", t("rules"), <Layers3 key="i" size={20} />, "Regulation-as-Code 規則與官方引用"],
    ["/admin/rule-versions", t("ruleVersions"), <FileClock key="i" size={20} />, "所有版本、生效期間與審查狀態"],
    ["/admin/legal-sources", t("sources"), <BookOpenText key="i" size={20} />, "官方資料來源與同步"],
    ["/admin/knowledge-base", t("knowledge"), <Database key="i" size={20} />, "條文、段落與向量索引"],
    ["/admin/agent-config", t("agentConfig"), <Bot key="i" size={20} />, "模型、限制與工具白名單"],
    ["/admin/evaluation", t("evaluation"), <FlaskConical key="i" size={20} />, "金融與法律正確性評估"],
    ["/admin/system-health", t("health"), <Activity key="i" size={20} />, "資料庫、模型與工作狀態"],
    ["/admin/audit-logs", t("audit"), <ScrollText key="i" size={20} />, "所有重要操作的稽核紀錄"],
    ["/admin/users", t("users"), <Users key="i" size={20} />, "帳號與角色"],
  ];
  return (
    <Guard>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {items.map(([href, title, icon, desc]) => (
          <Link key={href} href={href} className="flex gap-3 rounded-[12px] border border-line bg-surface p-5 shadow-card hover:border-brand">
            <span className="grid h-10 w-10 shrink-0 place-items-center rounded-[10px] bg-brand-soft text-brand">{icon}</span>
            <span><span className="block font-semibold text-ink">{title}</span><span className="text-[13px] text-ink-2">{desc}</span></span>
          </Link>
        ))}
      </div>
    </Guard>
  );
}

type QueueRule = { rule_id: string; version: string; rule_name: string; review_status: string; is_demo: boolean; citation_validated: boolean; has_official_source: boolean; citations: Citation[]; parameters: Record<string, string>; plain_language: string };

export function ReviewQueue() {
  const t = useTranslations("admin");
  const qc = useQueryClient();
  const allowed = useAdminGuard();
  const q = useQuery({ queryKey: ["review-queue"], enabled: allowed, queryFn: () => api<{ rules: QueueRule[]; regulatory_updates: { id: string; title: string; is_demo: boolean; review_status: string }[] }>("/admin/review-queue") });
  const [notes, setNotes] = useState<Record<string, string>>({});
  const review = useMutation({
    mutationFn: (v: { rule_id: string; version: string; decision: string }) => api(`/admin/rules/${v.rule_id}/review`, { body: { version: v.version, decision: v.decision, notes: notes[`${v.rule_id}@${v.version}`] ?? "" } }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["review-queue"] }); qc.invalidateQueries({ queryKey: ["rule-version"] }); },
  });
  const upd = useMutation({ mutationFn: (v: { id: string; decision: string }) => api(`/admin/regulatory/${v.id}/review`, { body: { decision: v.decision, notes: "" } }), onSuccess: () => qc.invalidateQueries({ queryKey: ["review-queue"] }) });
  if (!allowed) return <Guard>{null}</Guard>;
  return (
    <Guard>
      <div className="space-y-5">
        <Notice tone="warning">核准規則前，請逐字核對官方條文、適用條件與參數。核准紀錄會寫入審查與稽核紀錄；虛構示範規則無法啟用。</Notice>
        {review.error ? <ErrorState error={review.error} /> : null}
        {review.isSuccess ? <SuccessNote>已更新審查狀態</SuccessNote> : null}
        {q.isLoading ? <Card><LoadingBlock rows={6} /></Card> : q.error ? <Card><ErrorState error={q.error} /></Card> : (
          <>
            <Card>
              <CardHeader title="法規更新" />
              <ul className="divide-y divide-line px-5">
                {q.data!.regulatory_updates.length === 0 ? <li className="py-3 text-[13px] text-ink-3">沒有待審查的更新</li> : q.data!.regulatory_updates.map((u) => (
                  <li key={u.id} className="flex flex-wrap items-center gap-2 py-3">
                    <Link href={`/regulatory-monitor/updates?id=${u.id}`} className="flex-1 text-ink hover:text-brand">{u.title}</Link>
                    {u.is_demo ? <Badge tone="warning">示範</Badge> : null}
                    <Button size="sm" variant="secondary" onClick={() => upd.mutate({ id: u.id, decision: "approve" })}>{t("approve")}</Button>
                    <Button size="sm" variant="ghost" onClick={() => upd.mutate({ id: u.id, decision: "reject" })}>{t("reject")}</Button>
                  </li>
                ))}
              </ul>
            </Card>
            <ul className="space-y-3">
              {q.data!.rules.map((r) => {
                const key = `${r.rule_id}@${r.version}`;
                return (
                  <li key={key}>
                    <Card className="p-4">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-semibold text-ink">{r.rule_name}</span>
                        <span className="num text-[12px] text-ink-3">{key}</span>
                        <Badge tone={r.review_status === "approved" ? "normal" : "unknown"}>{r.review_status}</Badge>
                        {r.is_demo ? <Badge tone="warning">示範</Badge> : null}
                        {!r.has_official_source ? <Badge tone="warning">無官方來源</Badge> : <Badge tone={r.citation_validated ? "normal" : "critical"}>{r.citation_validated ? "引用已驗證" : "引用失敗"}</Badge>}
                      </div>
                      <p className="mt-1 text-[13px] text-ink-2">{r.plain_language}</p>
                      {Object.keys(r.parameters).length ? <p className="num mt-1 text-[12px] text-ink-3">參數：{JSON.stringify(r.parameters)}</p> : null}
                      <ul className="mt-2 space-y-1.5">{r.citations.map((c, i) => <CitationItem key={i} c={c} />)}</ul>
                      <div className="mt-3 flex flex-wrap items-center gap-2">
                        <Input aria-label={t("notes")} placeholder={t("notes")} value={notes[key] ?? ""} onChange={(e) => setNotes({ ...notes, [key]: e.target.value })} className="h-9 max-w-md" />
                        <Button size="sm" variant="secondary" onClick={() => review.mutate({ rule_id: r.rule_id, version: r.version, decision: "approve" })}>{t("approve")}</Button>
                        <Button size="sm" onClick={() => review.mutate({ rule_id: r.rule_id, version: r.version, decision: "activate" })}>{t("activate")}</Button>
                        <Button size="sm" variant="ghost" onClick={() => review.mutate({ rule_id: r.rule_id, version: r.version, decision: "reject" })}>{t("reject")}</Button>
                      </div>
                    </Card>
                  </li>
                );
              })}
            </ul>
          </>
        )}
      </div>
    </Guard>
  );
}

type RuleRow = { rule_id: string; rule_name: string; rule_type: string; trading_type: string; versions: { version: string; review_status: string; is_demo: boolean; effective_from: string | null; effective_to: string | null; citation_validated: boolean; has_official_source: boolean }[] };

export function RulesTable({ versionsOnly }: { versionsOnly?: boolean }) {
  const q = useQuery({ queryKey: ["rules-all"], queryFn: () => api<{ items: RuleRow[] }>("/rules", { auth: false }) });
  if (q.isLoading) return <Card><LoadingBlock rows={6} /></Card>;
  if (q.error) return <Card><ErrorState error={q.error} /></Card>;
  return (
    <Card className="overflow-x-auto">
      <table className="w-full min-w-[820px] text-[13px]">
        <thead><tr className="border-b border-line text-left text-ink-3"><th className="p-3">規則</th><th>類型</th><th>交易</th><th>版本</th><th>生效期間</th><th>狀態</th><th className="p-3">引用</th></tr></thead>
        <tbody>
          {q.data!.items.flatMap((r) => r.versions.map((v, i) => (
            <tr key={`${r.rule_id}@${v.version}`} className="border-b border-line">
              <td className="p-3">{i === 0 || versionsOnly ? <><p className="font-medium text-ink">{r.rule_name}</p><p className="num text-[11px] text-ink-3">{r.rule_id}</p></> : null}</td>
              <td className="text-ink-2">{r.rule_type}</td>
              <td className="text-ink-2">{r.trading_type}</td>
              <td className="num">{v.version}{v.is_demo ? <Badge tone="warning" className="ml-1">示範</Badge> : null}</td>
              <td className="num text-ink-2">{v.effective_from ?? "—"} ～ {v.effective_to ?? "—"}</td>
              <td><Badge tone={v.review_status === "active" ? "normal" : v.review_status === "approved" ? "blue" : "unknown"}>{v.review_status}</Badge></td>
              <td className="p-3">{v.has_official_source ? <Badge tone={v.citation_validated ? "normal" : "critical"}>{v.citation_validated ? "已驗證" : "失敗"}</Badge> : <Badge tone="warning">待查證</Badge>}</td>
            </tr>
          )))}
        </tbody>
      </table>
    </Card>
  );
}

export function LegalSources() {
  const qc = useQueryClient();
  const docs = useQuery({ queryKey: ["legal-docs"], queryFn: () => api<{ items: Parameters<typeof DocList>[0]["docs"] }>("/legal/documents", { auth: false }) });
  const sync = useMutation({ mutationFn: () => api<{ fetched_from_official_sources: boolean; created: string[]; unchanged: number; note: string | null }>("/admin/legal-sources/sync", { method: "POST" }), onSuccess: () => qc.invalidateQueries() });
  return (
    <Guard roles={["system_admin", "legal_reviewer"]}>
      <div className="space-y-4">
        <Card className="p-5">
          <Button onClick={() => sync.mutate()} disabled={sync.isPending}>比對官方資料版本</Button>
          {sync.error ? <ErrorState error={sync.error} /> : null}
          {sync.data ? <Notice tone="blue" title="比對結果">新偵測 {sync.data.created.length} 份變動、{sync.data.unchanged} 份未變動。{sync.data.note}</Notice> : null}
        </Card>
        <Card>{docs.isLoading ? <LoadingBlock /> : docs.data ? <DocList docs={docs.data.items} /> : null}</Card>
      </div>
    </Guard>
  );
}

function JsonCard({ path, title, roles }: { path: string; title: string; roles?: string[] }) {
  const allowed = useAdminGuard(roles);
  const q = useQuery({ queryKey: ["admin-json", path], enabled: allowed, queryFn: () => api<unknown>(path) });
  return (
    <Guard roles={roles}>
      <Card>
        <CardHeader title={title} />
        {q.isLoading ? <LoadingBlock /> : q.error ? <ErrorState error={q.error} /> : <pre className="max-h-[620px] overflow-auto p-5 text-[12px] text-ink-2">{JSON.stringify(q.data, null, 2)}</pre>}
      </Card>
    </Guard>
  );
}

export const KnowledgeBase = () => <JsonCard path="/admin/knowledge-base" title="知識庫" />;
export const AgentConfig = () => <JsonCard path="/admin/agent-config" title="Agent 設定" roles={["system_admin"]} />;
export const SystemHealth = () => <JsonCard path="/admin/system-health" title="系統健康" roles={["system_admin"]} />;

export function Evaluation() {
  const allowed = useAdminGuard();
  const q = useQuery({ queryKey: ["evaluation"], enabled: allowed, queryFn: () => api<Record<string, unknown>>("/admin/evaluation") });
  return (
    <Guard>
      <div className="space-y-4">
        <Notice tone="warning">評估結果由 scripts/run_evaluation.py 實際執行產生；沒有執行就顯示 NOT RUN。法律正確性仍需具金融法律知識的人員審查，AI 自評不能當作唯一證明。</Notice>
        <Card>{q.isLoading ? <LoadingBlock /> : q.error ? <ErrorState error={q.error} /> : <pre className="max-h-[640px] overflow-auto p-5 text-[12px] text-ink-2">{JSON.stringify(q.data, null, 2)}</pre>}</Card>
      </div>
    </Guard>
  );
}

export function AuditLogs() {
  const locale = useLocale();
  const allowed = useAdminGuard(["system_admin"]);
  const q = useQuery({ queryKey: ["audit"], enabled: allowed, queryFn: () => api<{ items: { id: string; actor_id: string | null; actor_type: string; action: string; resource_type: string; resource_id: string | null; metadata: unknown; request_id: string | null; created_at: string }[] }>("/admin/audit-logs") });
  if (!allowed) return <Guard roles={["system_admin"]}>{null}</Guard>;
  return (
    <Guard roles={["system_admin"]}>
      <Card className="overflow-x-auto">
        {q.isLoading ? <LoadingBlock /> : q.error ? <ErrorState error={q.error} /> : (
          <table className="w-full min-w-[820px] text-[12.5px]">
            <thead><tr className="border-b border-line text-left text-ink-3"><th className="p-3">時間</th><th>動作</th><th>資源</th><th>操作者</th><th className="p-3">Request ID</th></tr></thead>
            <tbody>{q.data!.items.map((a) => (
              <tr key={a.id} className="border-b border-line"><td className="num p-3 text-ink-2">{fmtDate(a.created_at, locale, true)}</td><td className="font-medium text-ink">{a.action}</td><td className="num text-ink-2">{a.resource_type}:{a.resource_id?.slice(0, 8) ?? "—"}</td><td className="num text-ink-2">{a.actor_type}:{a.actor_id?.slice(0, 8) ?? "—"}</td><td className="num p-3 text-ink-3">{a.request_id?.slice(0, 12) ?? "—"}</td></tr>
            ))}</tbody>
          </table>
        )}
      </Card>
    </Guard>
  );
}

export function UsersList() {
  const allowed = useAdminGuard(["system_admin"]);
  const q = useQuery({ queryKey: ["admin-users"], enabled: allowed, queryFn: () => api<{ items: { id: string; email: string; display_name: string; role: string; created_at: string }[] }>("/admin/users") });
  if (!allowed) return <Guard roles={["system_admin"]}>{null}</Guard>;
  return (
    <Guard roles={["system_admin"]}>
      <Card>
        {q.isLoading ? <LoadingBlock /> : q.error ? <ErrorState error={q.error} /> : (
          <ul className="divide-y divide-line px-5">{q.data!.items.map((u) => <li key={u.id} className="flex flex-wrap items-center gap-3 py-3"><span className="font-medium text-ink">{u.display_name}</span><span className="text-[13px] text-ink-3">{u.email}</span><Badge tone="blue">{u.role}</Badge></li>)}</ul>
        )}
      </Card>
    </Guard>
  );
}

export function ListIcon() {
  return <ListChecks size={18} />;
}
