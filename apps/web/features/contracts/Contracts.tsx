"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { CheckCircle2, FileText, ShieldAlert, Trash2, Upload } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";
import { Badge, Button, Card, CardHeader, EmptyState, ErrorState, Field, Input, LinkButton, LoadingBlock, Notice } from "@/components/ui";
import { API_URL, api } from "@/lib/api";
import { cn, fmtDate } from "@/lib/format";
import { useAuth } from "@/stores/auth";

type ContractRow = { id: string; document_name: string; broker_name: string | null; mime_type: string; size_bytes: number; document_hash: string; status: string; is_demo: boolean; uploaded_at: string };
type Clause = { id: string; clause_number: string | null; page_number: number; original_text: string; category: string; extracted_parameters: Record<string, string> };
type AIClause = { category: string; clause_number: string | null; quote: string; plain_language: string; party: string; verified_in_document: boolean };
type ContractDetail = ContractRow & { clauses: Clause[]; download_url: string; page_count: number | null; analysis: null | { provider: string; model_version: string | null; analysis_result: { ai_clauses: AIClause[]; note: string | null; not_found_categories: string[]; pending_questions: string[]; pii_redacted: Record<string, number>; extraction_notes: string[] } } };

export function ContractList() {
  const t = useTranslations("contracts");
  const locale = useLocale();
  const token = useAuth((s) => s.token);
  const q = useQuery({ queryKey: ["contracts", token], queryFn: () => api<{ items: ContractRow[] }>("/contracts"), enabled: !!token });
  if (!token) return <Card><EmptyState title={t("upload")} desc="登入後可以上傳契約；也可以使用虛構示範契約體驗分析流程。" action={<LinkButton href="/login" size="sm">登入</LinkButton>} /></Card>;
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        <LinkButton href="/contracts/upload"><Upload size={15} />{t("upload")}</LinkButton>
        <LinkButton href="/contracts/compare" variant="secondary">{t("compare")}</LinkButton>
      </div>
      <Card>
        {q.isLoading ? <LoadingBlock /> : q.error ? <ErrorState error={q.error} /> : q.data!.items.length === 0 ? <EmptyState icon={<FileText size={28} />} title="尚未上傳契約" action={<LinkButton href="/contracts/upload" size="sm">{t("upload")}</LinkButton>} /> : (
          <ul className="divide-y divide-line px-5">
            {q.data!.items.map((c) => (
              <li key={c.id} className="flex flex-wrap items-center gap-3 py-3">
                <FileText size={18} className="text-brand" />
                <Link href={`/contracts/${c.id}`} className="min-w-0 flex-1 font-medium text-ink hover:text-brand">{c.document_name}</Link>
                {c.is_demo ? <Badge tone="warning">虛構示範</Badge> : null}
                <Badge tone={c.status === "analyzed" ? "normal" : c.status === "failed" ? "critical" : "unknown"}>{t(`status.${c.status}`)}</Badge>
                <span className="num text-[12px] text-ink-3">{fmtDate(c.uploaded_at, locale, true)}</span>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}

export function ContractUpload() {
  const t = useTranslations("contracts");
  const router = useRouter();
  const token = useAuth((s) => s.token);
  const [file, setFile] = useState<File | null>(null);
  const [broker, setBroker] = useState("");
  const [ack, setAck] = useState(false);
  const up = useMutation({
    mutationFn: async () => {
      const fd = new FormData();
      fd.append("file", file!);
      fd.append("acknowledge_privacy", String(ack));
      if (broker) fd.append("broker_name", broker);
      const r = await api<{ id: string }>("/contracts/upload", { form: fd });
      await api(`/contracts/${r.id}/analyze`, { method: "POST" });
      return r;
    },
    onSuccess: (r) => router.push(`/contracts/${r.id}`),
  });
  const demo = useMutation({ mutationFn: () => api<{ id: string }>("/contracts/demo", { method: "POST" }), onSuccess: (r) => router.push(`/contracts/${r.id}`) });
  if (!token) return <Card><EmptyState title="請先登入" action={<LinkButton href="/login" size="sm">登入</LinkButton>} /></Card>;
  return (
    <div className="grid gap-5 lg:grid-cols-[1fr_360px]">
      <Card>
        <CardHeader title={t("upload")} />
        <div className="space-y-4 p-5">
          <Notice tone="warning" title={t("privacyTitle")}>
            <ul className="list-disc pl-5">{(t.raw("privacyItems") as string[]).map((x) => <li key={x}>{x}</li>)}</ul>
          </Notice>
          <Field label={t("choose")} htmlFor="contract-file">
            <label htmlFor="contract-file" className="flex cursor-pointer flex-col items-center justify-center gap-2 rounded-[12px] border-2 border-dashed border-line bg-surface-muted px-4 py-10 text-[14px] text-ink-2 hover:border-brand">
              <Upload size={22} />
              {file ? <span className="font-medium text-ink">{file.name}（{Math.round(file.size / 1024)} KB）</span> : <span>點一下選擇檔案</span>}
              <input id="contract-file" type="file" accept=".pdf,.png,.jpg,.jpeg,.txt,application/pdf,image/png,image/jpeg,text/plain" className="sr-only" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
            </label>
          </Field>
          <Field label={t("broker")} htmlFor="broker"><Input id="broker" value={broker} maxLength={60} onChange={(e) => setBroker(e.target.value)} /></Field>
          <label className="flex items-start gap-2 text-[14px] text-ink">
            <input type="checkbox" checked={ack} onChange={(e) => setAck(e.target.checked)} className="mt-1" />
            {t("privacyAck")}
          </label>
          <Button onClick={() => up.mutate()} disabled={!file || !ack || up.isPending}><Upload size={15} />{up.isPending ? "上傳中…" : t("analyze")}</Button>
          {up.error ? <ErrorState error={up.error} /> : null}
        </div>
      </Card>
      <Card className="self-start">
        <CardHeader title={t("demo")} desc="由系統產生的虛構契約（示範證券股份有限公司，非真實券商），用來體驗分析流程。" />
        <div className="p-5">
          <Button variant="secondary" onClick={() => demo.mutate()} disabled={demo.isPending}><FileText size={15} />{t("demo")}</Button>
          {demo.error ? <ErrorState error={demo.error} /> : null}
        </div>
      </Card>
    </div>
  );
}

export function ContractDetailView({ id }: { id: string }) {
  const t = useTranslations("contracts");
  const router = useRouter();
  const q = useQuery({
    queryKey: ["contract", id],
    queryFn: () => api<ContractDetail>(`/contracts/${id}`),
    refetchInterval: (qq) => (qq.state.data && ["uploaded", "analyzing"].includes(qq.state.data.status) ? 3000 : false),
  });
  const [active, setActive] = useState<string | null>(null);
  const del = useMutation({ mutationFn: () => api(`/contracts/${id}`, { method: "DELETE" }), onSuccess: () => router.push("/contracts") });
  if (q.isLoading) return <Card><LoadingBlock rows={8} /></Card>;
  if (q.error) return <Card><ErrorState error={q.error} /></Card>;
  const c = q.data!;
  const ai = c.analysis?.analysis_result;
  const isPdf = c.mime_type === "application/pdf";
  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="text-[24px] font-bold text-ink">{c.document_name}</h1>
          <p className="num mt-1 flex flex-wrap items-center gap-2 text-[12px] text-ink-3">
            <Badge tone={c.status === "analyzed" ? "normal" : "unknown"}>{t(`status.${c.status}`)}</Badge>
            {c.is_demo ? <Badge tone="warning">虛構示範</Badge> : null}
            SHA-256 #{c.document_hash.slice(0, 16)} · {c.page_count ?? "—"} 頁
          </p>
        </div>
        <Button variant="danger" size="sm" onClick={() => { if (confirm("確定刪除這份契約與分析結果？")) del.mutate(); }}><Trash2 size={14} />{"刪除"}</Button>
      </div>
      {["uploaded", "analyzing"].includes(c.status) ? <Card><LoadingBlock rows={4} /></Card> : null}
      {ai?.note ? <Notice tone="unknown">{ai.note}</Notice> : null}
      {ai?.extraction_notes?.map((n) => <Notice key={n} tone="warning">{n}</Notice>)}
      {ai && Object.keys(ai.pii_redacted ?? {}).length ? <Notice tone="blue">分析前已自動遮罩個資：{Object.entries(ai.pii_redacted).map(([k, v]) => `${k}×${v}`).join("、")}</Notice> : null}
      <div className="grid gap-4 xl:grid-cols-2">
        <Card className="overflow-hidden">
          <CardHeader title="原始文件" />
          <div className="p-4">
            {isPdf ? <iframe title="原始契約" src={`${API_URL}${c.download_url}`} className="h-[620px] w-full rounded-[8px] border border-line bg-white" /> : <p className="text-[13px] text-ink-3">此檔案類型無法預覽</p>}
          </div>
        </Card>
        <Card>
          <CardHeader title={t("clauses")} desc="點選條款可在下方看到 AI 白話說明（只顯示能在文件中找到原文的內容）" />
          <ul className="max-h-[680px] space-y-2 overflow-y-auto p-4">
            {c.clauses.map((cl) => {
              const notes = ai?.ai_clauses.filter((a) => a.clause_number === cl.clause_number || cl.original_text.replace(/\s/g, "").includes(a.quote.replace(/\s/g, "").slice(0, 20))) ?? [];
              return (
                <li key={cl.id}>
                  <button onClick={() => setActive(active === cl.id ? null : cl.id)} aria-expanded={active === cl.id} className={cn("w-full rounded-[12px] border p-3 text-left", active === cl.id ? "border-brand bg-brand-soft" : "border-line hover:bg-surface-muted")}>
                    <span className="flex flex-wrap items-center gap-2">
                      <span className="font-semibold text-ink">{cl.clause_number ?? "（未編號）"}</span>
                      <Badge tone="blue">{t(`categories.${cl.category}`)}</Badge>
                      <span className="text-[12px] text-ink-3">{t("page")} {cl.page_number}</span>
                      {Object.entries(cl.extracted_parameters).map(([k, v]) => <Badge key={k} tone="unknown">{k}={v}</Badge>)}
                    </span>
                    <span className="mt-1 block whitespace-pre-line text-[13px] text-ink-2">{cl.original_text}</span>
                  </button>
                  {active === cl.id ? (
                    <div className="mt-1 space-y-2 rounded-[12px] border border-line p-3 text-[13px]">
                      {notes.length ? notes.map((n, i) => (
                        <div key={i}>
                          <p className="flex items-center gap-2"><Badge tone="brand">{t(`party.${n.party}`)}</Badge><Badge tone="normal" icon={<CheckCircle2 size={11} />}>{t("verifiedQuote")}</Badge></p>
                          <p className="mt-1 text-ink">{n.plain_language}</p>
                        </div>
                      )) : <p className="text-ink-3">沒有可驗證的 AI 說明（AI 不可用或引用無法在文件中找到）。請以原文為準。</p>}
                      <p className="text-[12px] text-ink-3">條款內容不利於你，不代表條款違法或無效；有疑義可先向券商詢問或申訴。</p>
                    </div>
                  ) : null}
                </li>
              );
            })}
            {c.status === "analyzed" && c.clauses.length === 0 ? <EmptyState title="沒有擷取到條款" /> : null}
          </ul>
        </Card>
      </div>
      {ai ? (
        <div className="grid gap-4 md:grid-cols-2">
          <Card>
            <CardHeader title={t("notFound")} desc="以下類別在文件中找不到相關條款；系統不會自行補上預設內容" />
            <div className="flex flex-wrap gap-2 p-5">{ai.not_found_categories.length ? ai.not_found_categories.map((x) => <Badge key={x} tone="warning" icon={<ShieldAlert size={11} />}>{t(`categories.${x}`)}</Badge>) : <span className="text-[13px] text-ink-3">—</span>}</div>
          </Card>
          <Card>
            <CardHeader title={t("pending")} />
            <ul className="list-disc space-y-1 px-10 pb-5 pt-2 text-[13px] text-ink-2">{ai.pending_questions.length ? ai.pending_questions.map((x, i) => <li key={i}>{x}</li>) : <li>—</li>}</ul>
          </Card>
        </div>
      ) : null}
      <Card className="p-5">
        <p className="text-[14px] text-ink-2">把契約條款與模擬連動：在情境詳情頁按「AI 白話分析」時可指定這份契約，Agent 會引用相關原始條款。</p>
        <Link href="/scenarios" className="text-[14px] text-blue underline">前往模擬情境</Link>
      </Card>
    </div>
  );
}

export function ContractCompare() {
  const t = useTranslations("contracts");
  const token = useAuth((s) => s.token);
  const list = useQuery({ queryKey: ["contracts", token], queryFn: () => api<{ items: ContractRow[] }>("/contracts"), enabled: !!token });
  const [picked, setPicked] = useState<string[]>([]);
  const cmp = useMutation({ mutationFn: () => api<{ rows: { category: string; contracts: { contract_id: string; document_name: string; found: boolean; clauses: { clause_number: string; page_number: number; original_text: string }[] | null; message: string | null }[] }[]; note: string }>("/contracts/compare", { body: { contract_ids: picked } }) });
  if (!token) return <Card><EmptyState title="請先登入" /></Card>;
  return (
    <div className="space-y-4">
      <Notice tone="blue">{t("compareNote")}</Notice>
      <Card className="p-5">
        <ul className="grid gap-2 md:grid-cols-2">
          {list.data?.items.filter((c) => c.status === "analyzed").map((c) => (
            <li key={c.id}><label className="flex items-center gap-2 rounded-[10px] border border-line px-3 py-2 text-[14px]"><input type="checkbox" checked={picked.includes(c.id)} onChange={(e) => setPicked((p) => (e.target.checked ? [...p, c.id] : p.filter((x) => x !== c.id)))} />{c.document_name}</label></li>
          ))}
        </ul>
        <Button className="mt-3" onClick={() => cmp.mutate()} disabled={picked.length < 2 || cmp.isPending}>{t("compare")}</Button>
        {picked.length < 2 ? <p className="mt-2 text-[12px] text-ink-3">至少選兩份已分析的契約</p> : null}
        {cmp.error ? <ErrorState error={cmp.error} /> : null}
      </Card>
      {cmp.data ? (
        <Card className="overflow-x-auto">
          <table className="w-full min-w-[720px] text-[13px]">
            <thead><tr className="border-b border-line text-left text-ink-3"><th className="p-3">{t("category")}</th>{cmp.data.rows[0]?.contracts.map((c) => <th key={c.contract_id} className="p-3">{c.document_name}</th>)}</tr></thead>
            <tbody>
              {cmp.data.rows.map((r) => (
                <tr key={r.category} className="border-b border-line align-top">
                  <th scope="row" className="p-3 text-left font-medium text-ink">{t(`categories.${r.category}`)}</th>
                  {r.contracts.map((c) => (
                    <td key={c.contract_id} className="p-3 text-ink-2">
                      {c.found ? c.clauses!.map((cl, i) => <p key={i} className="mb-1"><span className="text-[11px] text-ink-3">{cl.clause_number}（{t("page")} {cl.page_number}）</span><br />{cl.original_text.slice(0, 180)}</p>) : <span className="text-warning">{c.message}</span>}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      ) : null}
    </div>
  );
}
