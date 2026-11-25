"use client";

import { useMutation } from "@tanstack/react-query";
import { Bot, Send, ShieldOff } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";
import { Badge, Button, Card, CardHeader, ErrorState } from "@/components/ui";
import { api } from "@/lib/api";
import { cn, fmtValue } from "@/lib/format";
import { useAuth } from "@/stores/auth";
import { CitationItem } from "../common/Timeline";

type Answer = {
  answer: string;
  kind: "answer" | "refusal" | "retrieval_only";
  citations: { id: string; official_title: string; article_number: string; official_url: string; version: string; content: string }[];
  comparison: null | { basis: string; new_price: string; before: Record<string, string>; after: Record<string, string>; labels: Record<string, string>; events_before: string[]; events_after: string[] };
  uncertainties?: string[];
  provider: string;
  model?: string;
  tool_calls: { tool: string }[];
};

/** 內嵌在模擬器與法律頁面的 Copilot：讀取目前的模擬參數，數字一律由計算引擎重算。 */
export function Copilot({ context }: { context?: { trading_type: string; input: Record<string, unknown> } }) {
  const t = useTranslations("copilot");
  const locale = useLocale();
  const token = useAuth((s) => s.token);
  const [msg, setMsg] = useState("");
  const [log, setLog] = useState<{ q: string; a: Answer }[]>([]);
  const m = useMutation({
    mutationFn: (q: string) => api<Answer>(token ? "/copilot/messages" : "/copilot/guest", { body: { message: q, context } }),
    onSuccess: (a, q) => setLog((l) => [...l, { q, a }]),
  });
  const send = (q: string) => {
    if (!q.trim() || m.isPending) return;
    setMsg("");
    m.mutate(q.trim());
  };
  return (
    <Card>
      <CardHeader title={<span className="flex items-center gap-2"><Bot size={18} className="text-brand" aria-hidden />{t("title")}</span>} desc={t("disclaimer")} />
      <div className="space-y-3 p-5">
        <div className="flex flex-wrap gap-2">
          {(t.raw("suggestions") as string[]).map((s) => (
            <button key={s} onClick={() => send(s)} className="rounded-full border border-line px-3 py-1 text-[12px] text-ink-2 hover:bg-surface-muted">{s}</button>
          ))}
        </div>
        <ul className="max-h-[420px] space-y-3 overflow-y-auto" aria-live="polite">
          {log.map((x, i) => (
            <li key={i} className="space-y-2">
              <p className="ml-auto w-fit max-w-[85%] rounded-[12px] bg-brand px-3 py-2 text-[13px] text-brand-fg">{x.q}</p>
              <div className={cn("rounded-[12px] border px-3 py-2 text-[13px]", x.a.kind === "refusal" ? "border-warning/40 bg-warning-soft" : "border-line bg-surface-muted")}>
                <div className="mb-1 flex flex-wrap gap-1.5">
                  {x.a.kind === "refusal" ? <Badge tone="warning" icon={<ShieldOff size={12} aria-hidden />}>{t("refusal")}</Badge> : null}
                  <Badge tone="unknown">{x.a.provider}{x.a.model ? `:${x.a.model}` : ""}</Badge>
                  {x.a.tool_calls.map((c, j) => <Badge key={j} tone="blue">{c.tool}</Badge>)}
                </div>
                <p className="whitespace-pre-line text-ink">{x.a.answer}</p>
                {x.a.comparison ? (
                  <div className="mt-2 rounded-[8px] border border-line bg-surface p-2">
                    <p className="mb-1 text-[12px] font-semibold text-ink-2">{t("comparison")}：{x.a.comparison.basis}</p>
                    <table className="num w-full text-[12px]">
                      <thead><tr className="text-ink-3"><th className="text-left font-normal" /><th className="text-right font-normal">{t("before")}</th><th className="text-right font-normal">{t("after")}</th></tr></thead>
                      <tbody>
                        {Object.keys(x.a.comparison.after).map((k) => (
                          <tr key={k} className="border-t border-line">
                            <td className="py-1 text-ink-2">{x.a.comparison!.labels[k]}</td>
                            <td className="text-right">{fmtValue(x.a.comparison!.before[k], k === "maintenance_ratio" ? "percent" : "TWD", locale)}</td>
                            <td className="text-right font-semibold">{fmtValue(x.a.comparison!.after[k], k === "maintenance_ratio" ? "percent" : "TWD", locale)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : null}
                {x.a.citations.length ? (
                  <details className="mt-2">
                    <summary className="cursor-pointer text-[12px] text-ink-2">{t("citations")}（{x.a.citations.length}）</summary>
                    <ul className="mt-1 space-y-1">
                      {x.a.citations.map((c) => (
                        <CitationItem key={c.id} c={{ source_key: c.id, official_title: c.official_title, article_number: c.article_number, official_url: c.official_url, version: c.version, quote: c.content.slice(0, 160) + (c.content.length > 160 ? "…" : ""), validated: true, authority: "官方原文", source_type: "", retrieved_at: "", validation_note: null }} />
                      ))}
                    </ul>
                  </details>
                ) : null}
              </div>
            </li>
          ))}
          {m.isPending ? <li className="text-[13px] text-ink-3">…</li> : null}
        </ul>
        {m.error ? <ErrorState error={m.error} /> : null}
        <form onSubmit={(e) => { e.preventDefault(); send(msg); }} className="flex gap-2">
          <label htmlFor="copilot-input" className="sr-only">{t("title")}</label>
          <input id="copilot-input" value={msg} onChange={(e) => setMsg(e.target.value)} maxLength={1000} placeholder={t("placeholder")} className="h-10 flex-1 rounded-full border border-line bg-surface px-4 text-[14px] text-ink" />
          <Button type="submit" disabled={m.isPending || !msg.trim()} aria-label={t("send")} className="rounded-full"><Send size={15} /></Button>
        </form>
      </div>
    </Card>
  );
}
