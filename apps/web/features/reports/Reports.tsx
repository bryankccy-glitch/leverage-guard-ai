"use client";

import { useQuery } from "@tanstack/react-query";
import { Download, FileText } from "lucide-react";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { Badge, Button, Card, CardHeader, EmptyState, ErrorState, LoadingBlock, Notice } from "@/components/ui";
import { api, download } from "@/lib/api";
import { fmtDate, fmtValue } from "@/lib/format";
import { useAuth } from "@/stores/auth";

type ReportRow = { id: string; report_number: string; report_type: string; calculation_version: string; rule_version: string; review_status: string; created_at: string };
type Section = { key: string; title: string; body: unknown };
type Report = ReportRow & { legal_source_version: string; model_version: string; report_content: { sections: Section[]; watermark: string; trading_type: string } };

export function ReportList() {
  const t = useTranslations("reports");
  const locale = useLocale();
  const token = useAuth((s) => s.token);
  const q = useQuery({ queryKey: ["reports", token], queryFn: () => api<{ items: ReportRow[] }>("/reports"), enabled: !!token });
  if (!token) return <Card><EmptyState title="登入後可以產生與保存報告" /></Card>;
  return (
    <Card>
      {q.isLoading ? <LoadingBlock /> : q.error ? <ErrorState error={q.error} /> : q.data!.items.length === 0 ? <EmptyState icon={<FileText size={28} />} title="尚無報告" desc={t("needRun")} action={<Link href="/scenarios" className="text-blue underline">前往模擬情境</Link>} /> : (
        <ul className="divide-y divide-line px-5">
          {q.data!.items.map((r) => (
            <li key={r.id} className="flex flex-wrap items-center gap-3 py-3">
              <Link href={`/reports/${r.id}`} className="num font-medium text-ink hover:text-brand">{r.report_number}</Link>
              <Badge tone="blue">{r.report_type === "investor" ? t("investor") : t("professional")}</Badge>
              <Badge tone="warning">{t("watermark")}</Badge>
              <span className="num ml-auto text-[12px] text-ink-3">{fmtDate(r.created_at, locale, true)}</span>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

export function ReportView({ id }: { id: string }) {
  const t = useTranslations("reports");
  const locale = useLocale();
  const q = useQuery({ queryKey: ["report", id], queryFn: () => api<Report>(`/reports/${id}`) });
  if (q.isLoading) return <Card><LoadingBlock rows={8} /></Card>;
  if (q.error) return <Card><ErrorState error={q.error} /></Card>;
  const r = q.data!;
  const meta: [string, string][] = [
    [t("meta.id"), r.report_number], [t("meta.generated"), fmtDate(r.created_at, locale, true)], [t("meta.calc"), r.calculation_version],
    [t("meta.rule"), r.rule_version], [t("meta.legal"), r.legal_source_version], [t("meta.model"), r.model_version ?? "—"], [t("meta.review"), t("watermark")],
  ];
  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-2">
        <h1 className="text-[24px] font-bold text-ink">{r.report_type === "investor" ? "個人金融法律風險報告（投資人版）" : "金融法律風險報告（專業版）"}</h1>
        <div className="ml-auto flex flex-wrap gap-2">
          <Button size="sm" onClick={() => download(`/reports/${id}/export?format=pdf`, `${r.report_number}.pdf`)}><Download size={14} />{t("exportPdf")}</Button>
          <Button size="sm" variant="secondary" onClick={() => download(`/reports/${id}/export?format=json`, `${r.report_number}.json`)}>{t("exportJson")}</Button>
          <Button size="sm" variant="secondary" onClick={() => download(`/reports/${id}/export?format=csv`, `${r.report_number}.csv`)}>{t("exportCsv")}</Button>
        </div>
      </div>
      <Notice tone="critical" title={r.report_content.watermark}>本報告由系統依模擬參數、規則引擎與官方條文產生，未經具金融法律專業的人員審查；不是投資建議或法律意見。</Notice>
      <Card className="overflow-x-auto">
        <table className="w-full text-[13px]"><tbody>
          {meta.map(([k, v]) => <tr key={k} className="border-b border-line"><th scope="row" className="w-40 bg-surface-muted p-2 text-left font-medium text-ink-2">{k}</th><td className="num p-2 text-ink">{v}</td></tr>)}
        </tbody></table>
      </Card>
      {r.report_content.sections.map((s) => (
        <Card key={s.key}>
          <CardHeader title={s.title} />
          <div className="p-5 text-[14px] text-ink-2"><SectionBody body={s.body} locale={locale} /></div>
        </Card>
      ))}
    </div>
  );
}

function SectionBody({ body, locale }: { body: unknown; locale: string }) {
  if (typeof body === "string") return <p className="whitespace-pre-line">{body}</p>;
  if (Array.isArray(body)) {
    if (body.length && typeof body[0] === "object" && body[0] !== null) {
      const rows = body as Record<string, unknown>[];
      if ("label" in rows[0] && "value" in rows[0]) {
        return (
          <table className="w-full"><tbody>
            {rows.map((r, i) => <tr key={i} className="border-b border-line"><td className="py-1.5">{String(r.label)}<p className="text-[11px] text-ink-3">{String(r.formula ?? "")}</p></td><td className="num text-right font-semibold text-ink">{fmtValue(r.value as string, String(r.unit), locale)}</td></tr>)}
          </tbody></table>
        );
      }
      const keys = Object.keys(rows[0]).slice(0, 5);
      return (
        <div className="overflow-x-auto"><table className="w-full min-w-[560px] text-[13px]">
          <thead><tr className="text-left text-ink-3">{keys.map((k) => <th key={k} className="pb-1 pr-3 font-medium">{k}</th>)}</tr></thead>
          <tbody>{rows.map((r, i) => <tr key={i} className="border-t border-line align-top">{keys.map((k) => <td key={k} className="py-1.5 pr-3">{typeof r[k] === "object" ? JSON.stringify(r[k]) : String(r[k] ?? "—")}</td>)}</tr>)}</tbody>
        </table></div>
      );
    }
    return <ul className="list-disc space-y-1 pl-5">{(body as unknown[]).map((x, i) => <li key={i}>{String(x)}</li>)}</ul>;
  }
  return <pre className="overflow-x-auto rounded-[8px] bg-surface-muted p-3 text-[12px]">{JSON.stringify(body, null, 1)}</pre>;
}
