"use client";

import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, CircleDashed, Loader2, XCircle } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { Badge, Card, CardHeader, ErrorState, Notice } from "@/components/ui";
import { API_URL, api } from "@/lib/api";
import { cn } from "@/lib/format";
import { useAuth } from "@/stores/auth";

export type AgentEvent = { seq: number; agent_name: string; status: string; message: string; created_at: string };

/** 用 fetch 讀取 SSE（EventSource 不能帶 Authorization 標頭）。事件都是後端寫入的真實執行紀錄。 */
export function useRunEvents(runId: string | null) {
  const token = useAuth((s) => s.token);
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [done, setDone] = useState<string | null>(null);
  useEffect(() => {
    if (!runId || !token) return;
    const ctrl = new AbortController();
    (async () => {
      try {
        const res = await fetch(`${API_URL}/api/v1/agents/runs/${runId}/events`, { headers: { Authorization: `Bearer ${token}` }, signal: ctrl.signal });
        const reader = res.body?.getReader();
        if (!reader) return;
        const dec = new TextDecoder();
        let buf = "";
        for (;;) {
          const { value, done: end } = await reader.read();
          if (end) break;
          buf += dec.decode(value, { stream: true });
          const chunks = buf.split("\n\n");
          buf = chunks.pop() ?? "";
          for (const c of chunks) {
            const ev = /event: (\w+)/.exec(c)?.[1];
            const data = /data: (.*)/.exec(c)?.[1];
            if (!data) continue;
            const parsed = JSON.parse(data);
            if (ev === "done") setDone(parsed.status);
            else setEvents((prev) => [...prev, parsed]);
          }
        }
      } catch {
        /* 中斷或離開頁面 */
      }
    })();
    return () => ctrl.abort();
  }, [runId, token]);
  return { events, done };
}

const AGENT_ORDER = ["orchestrator", "financial_calculation", "legal_rules", "legal_retrieval", "contract", "verification", "plain_language", "review", "report"];

export function RunProgress({ runId, cached }: { runId: string; cached?: boolean }) {
  const t = useTranslations("agents");
  const { events, done } = useRunEvents(cached ? null : runId);
  const run = useQuery({
    queryKey: ["agent-run", runId, done, cached],
    queryFn: () => api<RunDetail>(`/agents/runs/${runId}`),
    refetchInterval: (q) => (q.state.data?.status === "running" || q.state.data?.status === "queued" ? 4000 : false),
  });
  const latest: Record<string, string> = {};
  for (const e of events) latest[e.agent_name] = e.status;
  if (run.data?.tasks) for (const tk of run.data.tasks) latest[tk.agent_name] = tk.status;
  const agents = AGENT_ORDER.filter((a) => a !== "contract" || latest.contract);
  return (
    <Card>
      <CardHeader title={t("live")} desc={<Link className="text-blue hover:underline" href={`/agents/runs/${runId}`}>{runId.slice(0, 8)}…</Link>} action={run.data ? <RunStatus status={run.data.status} /> : null} />
      <ol className="grid gap-2 p-5 sm:grid-cols-3" aria-live="polite">
        {agents.map((a) => {
          const s = latest[a] ?? "queued";
          return (
            <li key={a} className={cn("flex items-center gap-2 rounded-[10px] border px-3 py-2 text-[13px]", s === "running" ? "border-blue bg-blue-soft" : "border-line")}>
              {s === "completed" ? <CheckCircle2 size={15} className="text-normal" aria-hidden /> : s === "failed" ? <XCircle size={15} className="text-critical" aria-hidden /> : s === "running" ? <Loader2 size={15} className="animate-spin text-blue" aria-hidden /> : <CircleDashed size={15} className="text-ink-3" aria-hidden />}
              <span className="flex-1 truncate">{a}</span>
              <span className="text-[11px] text-ink-3">{t.has(`status.${s}`) ? t(`status.${s}`) : s}</span>
            </li>
          );
        })}
      </ol>
      {events.length ? (
        <ul className="mx-5 mb-5 max-h-40 space-y-0.5 overflow-y-auto rounded-[8px] bg-surface-muted p-2 font-mono text-[11.5px] text-ink-2">
          {events.map((e) => (
            <li key={e.seq}>#{e.seq} [{e.agent_name}] {e.message}</li>
          ))}
        </ul>
      ) : null}
      {run.error ? <ErrorState error={run.error} /> : null}
      {run.data?.status === "completed" && run.data.output ? <RunOutput output={run.data.output} /> : null}
      {run.data?.status === "failed" ? <div className="px-5 pb-5"><Notice tone="critical">{run.data.error_message}</Notice></div> : null}
    </Card>
  );
}

export function RunStatus({ status }: { status: string }) {
  const t = useTranslations("agents.status");
  const tone = status === "completed" ? "normal" : status === "failed" ? "critical" : status === "running" ? "blue" : "unknown";
  return <Badge tone={tone}>{t.has(status) ? t(status) : status}</Badge>;
}

export type RunDetail = {
  id: string;
  status: string;
  provider: string;
  model: string;
  total_tokens: number;
  error_message: string | null;
  scenario_id: string | null;
  created_at: string;
  completed_at: string | null;
  output: RunOutputData | null;
  tasks: { id: string; agent_name: string; task_type: string; status: string; depends_on: string[]; output_summary: string; tool_calls: unknown[]; retrieved_sources: { id: string; title: string; article: string; url: string; version: string }[]; validation_result: unknown; tokens: number; error_message: string | null; started_at: string; finished_at: string; duration_ms: number }[];
};

export type RunOutputData = {
  summary: string;
  financial_explanation: { summary: string; assumptions: string[] };
  legal_events: { event_type: string; title: string; status: string; date: string | null; explanation: string; legal_citation_ids: string[] }[];
  investor_rights: { description: string }[];
  investor_obligations: { description: string }[];
  uncertainties: string[];
  limitations: string[];
  official_resources: { name: string; url: string; note: string }[];
  explanation_provider: string;
  explanation_model: string | null;
  review: { passed: boolean; advice_violations: string[]; unverified_numbers: string[] };
  verification: { citations_total: number; citations_failed: number; metrics_unchanged: boolean };
  calculation_version: string;
  rule_version: string;
};

function RunOutput({ output }: { output: RunOutputData }) {
  const tc = useTranslations("common");
  const ai = output.explanation_provider !== "template";
  return (
    <div className="space-y-3 border-t border-line p-5 text-[14px]">
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone={ai ? "brand" : "unknown"}>{ai ? `AI：${output.explanation_provider} ${output.explanation_model ?? ""}` : "規則模板（未使用生成式 AI）"}</Badge>
        <Badge tone={output.review.passed ? "normal" : "warning"}>Review {output.review.passed ? "passed" : "fallback"}</Badge>
        <Badge tone={output.verification.citations_failed === 0 ? "normal" : "critical"}>引用 {output.verification.citations_total} / 失敗 {output.verification.citations_failed}</Badge>
        <Badge tone={output.verification.metrics_unchanged ? "normal" : "critical"}>數字未被 AI 修改：{output.verification.metrics_unchanged ? tc("yes") : tc("no")}</Badge>
      </div>
      {ai ? <p className="text-[12px] text-ink-3">AI 白話說明僅供理解參考；正式數字與法律依據以計算結果與官方條文為準。</p> : null}
      <p className="text-ink">{output.summary}</p>
      <p className="rounded-[8px] bg-surface-muted p-3 text-ink-2">{output.financial_explanation.summary}</p>
      <ul className="space-y-2">
        {output.legal_events.filter((e) => e.explanation && e.event_type !== "price_change").slice(0, 10).map((e, i) => (
          <li key={i} className="rounded-[8px] border border-line p-3">
            <p className="font-medium text-ink">{e.title}</p>
            <p className="mt-0.5 whitespace-pre-line text-[13px] text-ink-2">{e.explanation}</p>
          </li>
        ))}
      </ul>
      {output.uncertainties.length ? (
        <Notice tone="warning" title="尚待確認">
          <ul className="list-disc pl-5">{output.uncertainties.map((u, i) => <li key={i}>{u}</li>)}</ul>
        </Notice>
      ) : null}
      <ul className="list-disc space-y-0.5 pl-5 text-[12px] text-ink-3">{output.limitations.map((l, i) => <li key={i}>{l}</li>)}</ul>
    </div>
  );
}
