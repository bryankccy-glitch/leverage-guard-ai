"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bell, CheckCheck } from "lucide-react";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { useTheme } from "next-themes";
import { useState } from "react";
import { demoSwap, useL } from "@/lib/i18n";
import { Badge, Button, Card, CardHeader, EmptyState, ErrorState, Field, Input, LoadingBlock, Select, SuccessNote } from "@/components/ui";
import { api } from "@/lib/api";
import { cn, fmtDate } from "@/lib/format";
import { useAuth, useUI } from "@/stores/auth";

export function HistoryView() {
  const locale = useLocale();
  const L = useL();
  const isEn = locale === "en";
  const token = useAuth((s) => s.token);
  const q = useQuery({ queryKey: ["history", token], queryFn: () => api<{ items: { id: string; scenario_id: string; scenario_name: string; scenario_type: string; calculation_version: string; rule_version_label: string; created_at: string }[] }>("/history"), enabled: !!token });
  if (!token) return <Card><EmptyState title={L("登入後可以查看模擬紀錄", "Log in to see your simulation history")} /></Card>;
  return (
    <Card className="overflow-x-auto">
      {q.isLoading ? <LoadingBlock /> : q.error ? <ErrorState error={q.error} /> : q.data!.items.length === 0 ? <EmptyState title={L("尚無紀錄", "No records yet")} /> : (
        <table className="w-full min-w-[640px] text-[13px]">
          <thead><tr className="border-b border-line text-left text-ink-3"><th className="p-3">{L("時間", "Time")}</th><th>{L("情境", "Scenario")}</th><th>{L("類型", "Type")}</th><th>{L("計算版本", "Calculation version")}</th><th className="p-3">{L("規則版本", "Rule version")}</th></tr></thead>
          <tbody>
            {q.data!.items.map((r) => (
              <tr key={r.id} className="border-b border-line">
                <td className="num p-3 text-ink-2">{fmtDate(r.created_at, locale, true)}</td>
                <td><Link href={`/scenarios/${r.scenario_id}`} className="text-ink hover:text-brand">{demoSwap(r.scenario_name, isEn)}</Link></td>
                <td><Badge tone="unknown">{r.scenario_type}</Badge></td>
                <td className="num">{r.calculation_version}</td>
                <td className="num p-3">{r.rule_version_label}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Card>
  );
}

type Notif = { id: string; notification_type: string; category: string; title: string; message: string; resource_type: string | null; resource_id: string | null; read_at: string | null; created_at: string };

export function NotificationsView() {
  const t = useTranslations("notifications");
  const L = useL();
  const locale = useLocale();
  const token = useAuth((s) => s.token);
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["notifications", token], queryFn: () => api<{ items: Notif[] }>("/notifications"), enabled: !!token });
  const subs = useQuery({ queryKey: ["subs", token], queryFn: () => api<{ items: { topic: string; digest: boolean }[] }>("/notifications/subscriptions"), enabled: !!token });
  const readAll = useMutation({ mutationFn: () => api("/notifications/read-all", { method: "POST" }), onSuccess: () => qc.invalidateQueries({ queryKey: ["notifications"] }) });
  const read = useMutation({ mutationFn: (id: string) => api(`/notifications/${id}/read`, { method: "PATCH" }), onSuccess: () => qc.invalidateQueries({ queryKey: ["notifications"] }) });
  const [topicsEdit, setTopics] = useState<string[] | null>(null);
  const [digestEdit, setDigest] = useState<boolean | null>(null);
  const topics = topicsEdit ?? subs.data?.items.map((s) => s.topic) ?? [];
  const digest = digestEdit ?? subs.data?.items.some((s) => s.digest) ?? false;
  const save = useMutation({ mutationFn: () => api("/notifications/subscriptions", { method: "PUT", body: { topics, digest } }) });
  if (!token) return <Card><EmptyState title={L("登入後可以查看通知", "Log in to see notifications")} /></Card>;
  const href = (n: Notif) => (n.resource_type === "contract" ? `/contracts/${n.resource_id}` : n.resource_type === "report" ? `/reports/${n.resource_id}` : "#");
  return (
    <div className="grid gap-5 lg:grid-cols-[1fr_340px]">
      <Card>
        <CardHeader title={t("title")} action={<Button size="sm" variant="secondary" onClick={() => readAll.mutate()}><CheckCheck size={14} />{t("markAll")}</Button>} />
        {q.isLoading ? <LoadingBlock /> : q.error ? <ErrorState error={q.error} /> : q.data!.items.length === 0 ? <EmptyState icon={<Bell size={28} />} title={L("沒有通知", "No notifications")} /> : (
          <ul className="divide-y divide-line px-5">
            {q.data!.items.map((n) => (
              <li key={n.id} className={cn("flex flex-wrap items-start gap-3 py-3", !n.read_at && "font-medium")}>
                <span aria-hidden className={cn("mt-1.5 h-2 w-2 rounded-full", n.read_at ? "bg-line" : "bg-blue")} />
                <div className="min-w-0 flex-1">
                  <p className="flex flex-wrap items-center gap-2 text-ink">{n.title}<Badge tone={n.category === "real_regulation" ? "blue" : n.category === "simulation" ? "unknown" : n.category === "pending_regulation" ? "warning" : "unknown"}>{t(`category.${n.category}`)}</Badge></p>
                  <p className="text-[13px] font-normal text-ink-2">{n.message}</p>
                  {n.resource_id ? <Link href={href(n)} className="text-[12px] font-normal text-blue underline">{L("查看", "View")}</Link> : null}
                </div>
                <span className="num text-[12px] font-normal text-ink-3">{fmtDate(n.created_at, locale, true)}</span>
                {!n.read_at ? <button onClick={() => read.mutate(n.id)} className="text-[12px] font-normal text-blue">{L("已讀", "Mark as read")}</button> : null}
              </li>
            ))}
          </ul>
        )}
      </Card>
      <Card className="self-start">
        <CardHeader title={t("subscriptions")} desc={L("通知會區分：模擬情境變動、真實法規更新、待審查的法規候選", "Notifications are grouped as: simulation changes, real regulatory updates, and regulatory candidates awaiting review")} />
        <div className="space-y-2 p-5">
          {(["margin_rules", "day_trading_rules", "legal_document", "saved_scenario_rules"] as const).map((k) => (
            <label key={k} className="flex items-center gap-2 text-[14px] text-ink"><input type="checkbox" checked={topics.includes(k)} onChange={(e) => setTopics(e.target.checked ? [...topics, k] : topics.filter((x) => x !== k))} />{t(`topics.${k}`)}</label>
          ))}
          <label className="flex items-center gap-2 text-[14px] text-ink"><input type="checkbox" checked={digest} onChange={(e) => setDigest(e.target.checked)} />{L("Digest（彙整通知）", "Digest (bundled notifications)")}</label>
          <Button size="sm" onClick={() => save.mutate()} disabled={save.isPending}>{L("儲存", "Save")}</Button>
          {save.isSuccess ? <SuccessNote>{L("已儲存", "Saved")}</SuccessNote> : null}
          <p className="text-[12px] text-ink-3">{L("Email 通知為選配功能，目前未設定寄信服務，只提供站內通知。", "Email notifications are optional; no mail service is configured, so only in-app notifications are available.")}</p>
        </div>
      </Card>
    </div>
  );
}

export function SettingsView() {
  const t = useTranslations("settings");
  const L = useL();
  const token = useAuth((s) => s.token);
  const { theme, setTheme } = useTheme();
  const locale = useUI((s) => s.locale);
  const setLocale = useUI((s) => s.setLocale);
  const me = useQuery({ queryKey: ["me", token], queryFn: () => api<{ display_name: string; email: string; role: string }>("/me"), enabled: !!token });
  const [nameEdit, setName] = useState<string | null>(null);
  const name = nameEdit ?? me.data?.display_name ?? "";
  const save = useMutation({ mutationFn: () => api("/me", { method: "PATCH", body: { display_name: name, preferred_language: locale, theme: theme ?? "light" } }) });
  return (
    <div className="grid gap-5 lg:grid-cols-2">
      <Card>
        <CardHeader title={t("profile")} />
        <div className="space-y-4 p-5">
          {token ? (
            <>
              <p className="text-[13px] text-ink-3">{me.data?.email}</p>
              <Field label={t("displayName")} htmlFor="dn"><Input id="dn" value={name} maxLength={80} onChange={(e) => setName(e.target.value)} /></Field>
            </>
          ) : <p className="text-[13px] text-ink-3">{L("訪客模式：偏好只存在這台瀏覽器。", "Guest mode: preferences are stored only in this browser.")}</p>}
          <Field label={t("language")} htmlFor="lang">
            <Select id="lang" value={locale} onChange={(e) => setLocale(e.target.value as "zh-TW" | "en")}><option value="zh-TW">繁體中文</option><option value="en">English</option></Select>
          </Field>
          <Field label={t("theme")} htmlFor="theme">
            <Select id="theme" value={theme ?? "light"} onChange={(e) => setTheme(e.target.value)}><option value="light">{t("light")}</option><option value="dark">{t("dark")}</option><option value="system">{t("system")}</option></Select>
          </Field>
          {token ? <Button onClick={() => save.mutate()} disabled={save.isPending}>{L("儲存", "Save")}</Button> : null}
          {save.isSuccess ? <SuccessNote>{L("已儲存", "Saved")}</SuccessNote> : null}
          {save.error ? <ErrorState error={save.error} /> : null}
        </div>
      </Card>
      <Card className="self-start">
        <CardHeader title={t("privacy")} />
        <div className="space-y-2 p-5 text-[14px] text-ink-2">
          <p>{t("deleteNote")}</p>
          <p>{L("私人資料以資料庫 Row Level Security 隔離；系統管理員沒有預設讀取你契約的權限。", "Private data is isolated with database Row Level Security; system admins have no default access to your contracts.")}</p>
          <Link href="/privacy" className="text-blue underline">{L("隱私政策", "Privacy policy")}</Link>
        </div>
      </Card>
    </div>
  );
}
