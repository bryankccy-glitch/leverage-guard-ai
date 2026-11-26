"use client";

import "@xyflow/react/dist/style.css";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Background, Controls, MarkerType, ReactFlow, type Edge, type Node } from "@xyflow/react";
import { RotateCcw, XCircle } from "lucide-react";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { useTheme } from "next-themes";
import { useIsEn, useL } from "@/lib/i18n";
import { Badge, Button, Card, CardHeader, EmptyState, ErrorState, LoadingBlock, Notice } from "@/components/ui";
import { api } from "@/lib/api";
import { fmtDate, useMounted } from "@/lib/format";
import { useAuth } from "@/stores/auth";
import { RunProgress, RunStatus, type RunDetail } from "./RunProgress";

type AgentInfo = { name: string; description: string; kind: string; model: string | null; provider: string; executions: number; success_rate: string; avg_duration_ms: number | null; token_usage: number; estimated_cost: string | null; last_run: string | null };

const FLOW: { id: string; label: string; labelEn?: string; x: number; y: number; kind: "agent" | "tool" | "gate" }[] = [
  { id: "input", label: "使用者輸入", labelEn: "User input", x: 0, y: 120, kind: "tool" },
  { id: "orchestrator", label: "Orchestrator", x: 170, y: 120, kind: "agent" },
  { id: "financial_calculation", label: "Financial Calc", x: 360, y: 20, kind: "agent" },
  { id: "engine", label: "Financial Engine（Decimal）", x: 560, y: 20, kind: "tool" },
  { id: "legal_rules", label: "Legal Rules", x: 360, y: 120, kind: "agent" },
  { id: "rules", label: "Regulation-as-Code", x: 560, y: 120, kind: "tool" },
  { id: "legal_retrieval", label: "Legal Retrieval", x: 360, y: 220, kind: "agent" },
  { id: "rag", label: "Legal RAG（pgvector）", x: 560, y: 220, kind: "tool" },
  { id: "contract", label: "Contract（選用）", labelEn: "Contract (optional)", x: 360, y: 320, kind: "agent" },
  { id: "verification", label: "Verification", x: 780, y: 120, kind: "agent" },
  { id: "plain_language", label: "Plain Language（千問）", labelEn: "Plain Language (Qwen)", x: 970, y: 120, kind: "agent" },
  { id: "review", label: "Review Gate", x: 1170, y: 120, kind: "gate" },
  { id: "report", label: "Report", x: 1350, y: 120, kind: "agent" },
];
const EDGES: [string, string, string?, string?][] = [
  ["input", "orchestrator"], ["orchestrator", "financial_calculation"], ["financial_calculation", "engine"], ["orchestrator", "legal_rules"],
  ["legal_rules", "rules"], ["orchestrator", "legal_retrieval"], ["legal_retrieval", "rag"], ["orchestrator", "contract", "有契約時", "if contract"],
  ["engine", "verification"], ["rules", "verification"], ["rag", "verification"], ["contract", "verification"],
  ["verification", "plain_language"], ["plain_language", "review"], ["review", "report", "通過", "pass"], ["review", "report", "未通過→模板", "fail → template"],
];

export function WorkflowGraph({ statuses }: { statuses?: Record<string, string> }) {
  const { resolvedTheme } = useTheme();
  const mounted = useMounted();
  const L = useL();
  const isEn = useIsEn();
  const color = (id: string) => {
    const s = statuses?.[id];
    return s === "completed" ? "var(--risk-normal)" : s === "failed" ? "var(--risk-critical)" : s === "running" ? "var(--blue)" : "var(--border)";
  };
  const nodes: Node[] = FLOW.map((f) => ({
    id: f.id, position: { x: f.x, y: f.y }, data: { label: isEn && f.labelEn ? f.labelEn : f.label },
    style: { borderRadius: f.kind === "gate" ? 999 : 10, border: `2px solid ${color(f.id)}`, background: f.kind === "tool" ? "var(--surface-muted)" : "var(--surface)", color: "var(--text)", fontSize: 12, width: f.kind === "tool" ? 170 : 150, padding: 8 },
  }));
  const edges: Edge[] = EDGES.map(([s, t, label, labelEn], i) => ({ id: `e${i}`, source: s, target: t, label: isEn ? labelEn : label, animated: statuses?.[t] === "running", markerEnd: { type: MarkerType.ArrowClosed }, style: { stroke: "var(--text-3)" }, labelStyle: { fontSize: 10, fill: "var(--text-3)" } }));
  if (!mounted) return <div className="skeleton h-[380px] rounded-[12px]" />;
  return (
    <div className="h-[380px] rounded-[12px] border border-line" role="img" aria-label={L("Agent 工作流程：Orchestrator 分派計算、規則、檢索（與選用的契約）→ 驗證 → 白話說明 → 審查閘門 → 報告", "Agent workflow: the orchestrator dispatches calculation, rules and retrieval (plus the optional contract) → verification → plain-language explanation → review gate → report")}>
      <ReactFlow nodes={nodes} edges={edges} fitView forceColorMode={resolvedTheme === "dark" ? "dark" : "light"} nodesDraggable={false} nodesConnectable={false} proOptions={{ hideAttribution: true }}>
        <Background />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}

export function AgentsCenter() {
  const isEn = useIsEn();
  const t = useTranslations("agents");
  const L = useL();
  const locale = useLocale();
  const token = useAuth((s) => s.token);
  const agents = useQuery({ queryKey: ["agents", token], queryFn: () => api<{ items: AgentInfo[]; provider: { provider: string; model: string } }>("/agents"), enabled: !!token });
  const runs = useQuery({ queryKey: ["agent-runs", token], queryFn: () => api<{ items: { id: string; workflow_name: string; status: string; provider: string; model: string; total_tokens: number; created_at: string; error_message: string | null }[] }>("/agents/runs"), enabled: !!token });
  return (
    <div className="space-y-5">
      <Card>
        <CardHeader title={t("workflow")} desc={L("確定性工具（灰底）負責數字與規則；LLM 只負責白話說明，並經過審查閘門", "Deterministic tools (grey) handle numbers and rules; the LLM only writes plain-language explanations, which pass a review gate")} />
        <div className="p-5"><WorkflowGraph /></div>
      </Card>
      {!token ? <Card><EmptyState title={L("登入後可查看 Agent 統計與執行紀錄", "Log in to see agent statistics and run history")} /></Card> : (
        <>
          <Card className="overflow-x-auto">
            <CardHeader title="Agents" desc={agents.data ? `LLM${isEn ? ": " : "："}${agents.data.provider.provider} ${agents.data.provider.model ?? ""}` : undefined} />
            {agents.isLoading ? <LoadingBlock /> : agents.error ? <ErrorState error={agents.error} /> : (
              <table className="w-full min-w-[820px] text-[13px]">
                <thead><tr className="border-b border-line text-left text-ink-3">
                  <th className="p-3">{t("agent")}</th><th>{L("類型", "Type")}</th><th>{t("model")}</th><th className="text-right">{t("executions")}</th><th className="text-right">{t("successRate")}</th><th className="text-right">{t("avgDuration")}</th><th className="text-right">{t("tokens")}</th><th className="p-3 text-right">{t("cost")}</th>
                </tr></thead>
                <tbody>
                  {agents.data!.items.map((a) => (
                    <tr key={a.name} className="border-b border-line">
                      <td className="p-3"><p className="font-medium text-ink">{a.name}</p><p className="text-[12px] text-ink-3">{a.description}</p></td>
                      <td><Badge tone={a.kind === "llm" ? "brand" : a.kind === "hybrid" ? "blue" : "unknown"}>{t(`kind.${a.kind}`)}</Badge></td>
                      <td className="num text-ink-2">{a.model ?? "—"}</td>
                      <td className="num text-right">{a.executions}</td>
                      <td className="num text-right">{a.executions ? `${a.success_rate}%` : "—"}</td>
                      <td className="num text-right">{a.avg_duration_ms !== null ? `${a.avg_duration_ms} ms` : "—"}</td>
                      <td className="num text-right">{a.token_usage}</td>
                      <td className="num p-3 text-right text-ink-3">{a.estimated_cost ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Card>
          <Card>
            <CardHeader title={t("runs")} />
            {runs.isLoading ? <LoadingBlock /> : runs.data?.items.length ? (
              <ul className="divide-y divide-line px-5">
                {runs.data.items.map((r) => (
                  <li key={r.id} className="flex flex-wrap items-center gap-3 py-3 text-[13px]">
                    <Link href={`/agents/runs/${r.id}`} className="num font-medium text-ink hover:text-brand">{r.id.slice(0, 8)}</Link>
                    <span className="text-ink-2">{r.workflow_name}</span>
                    <RunStatus status={r.status} />
                    <span className="num text-ink-3">{r.provider}:{r.model} · {r.total_tokens} tokens</span>
                    <span className="num ml-auto text-ink-3">{fmtDate(r.created_at, locale, true)}</span>
                  </li>
                ))}
              </ul>
            ) : <EmptyState title={L("尚無執行紀錄", "No runs yet")} desc={L("在模擬器按「AI 白話分析」就會建立一筆執行", "Press \"AI plain-language analysis\" in a simulator to create a run")} />}
          </Card>
        </>
      )}
    </div>
  );
}

export function AgentRunView({ id }: { id: string }) {
  const t = useTranslations("agents");
  const L = useL();
  const q = useQuery({ queryKey: ["agent-run-detail", id], queryFn: () => api<RunDetail>(`/agents/runs/${id}`), refetchInterval: (qq) => (["queued", "running"].includes(qq.state.data?.status ?? "") ? 3000 : false) });
  const cancel = useMutation({ mutationFn: () => api(`/agents/runs/${id}/cancel`, { method: "POST" }), onSuccess: () => q.refetch() });
  const retry = useMutation({ mutationFn: () => api<{ run_id: string }>(`/agents/runs/${id}/retry`, { method: "POST" }) });
  if (q.isLoading) return <Card><LoadingBlock rows={6} /></Card>;
  if (q.error) return <Card><ErrorState error={q.error} /></Card>;
  const r = q.data!;
  const statuses = Object.fromEntries(r.tasks.map((x) => [x.agent_name, x.status]));
  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-2">
        <h1 className="num text-[22px] font-bold text-ink">Run {r.id.slice(0, 8)}</h1>
        <RunStatus status={r.status} />
        <Badge tone="unknown">{r.provider}:{r.model}</Badge>
        <Badge tone="unknown">{r.total_tokens} tokens</Badge>
        <div className="ml-auto flex gap-2">
          {["queued", "running"].includes(r.status) ? <Button size="sm" variant="secondary" onClick={() => cancel.mutate()}><XCircle size={14} />{t("cancel")}</Button> : null}
          {["failed", "cancelled"].includes(r.status) ? <Button size="sm" variant="secondary" onClick={() => retry.mutate()}><RotateCcw size={14} />{t("retry")}</Button> : null}
        </div>
      </div>
      {retry.data ? <Notice tone="normal">{L("已建立新的執行：", "New run created: ")}<Link className="underline" href={`/agents/runs/${retry.data.run_id}`}>{retry.data.run_id.slice(0, 8)}</Link></Notice> : null}
      {retry.error ? <ErrorState error={retry.error} /> : null}
      <Card className="p-5"><WorkflowGraph statuses={statuses} /></Card>
      <Card>
        <CardHeader title={L("執行時間軸", "Run timeline")} desc={L("只顯示可稽核的工具呼叫、資料來源、輸出摘要與驗證結果，不顯示模型的隱藏思考過程", "Shows only auditable tool calls, data sources, output summaries and verification results, not the model's hidden reasoning")} />
        <ol className="space-y-3 p-5">
          {r.tasks.map((tk) => (
            <li key={tk.id} className="rounded-[12px] border border-line p-3 text-[13px]">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-semibold text-ink">{tk.agent_name}</span>
                <span className="text-ink-3">{tk.task_type}</span>
                <RunStatus status={tk.status} />
                <span className="num ml-auto text-ink-3">{tk.duration_ms ?? "—"} ms · {tk.tokens} tokens</span>
              </div>
              <p className="mt-1 text-ink-2">{tk.output_summary}</p>
              {tk.error_message ? <p className="mt-1 text-critical">{tk.error_message}</p> : null}
              {(tk.tool_calls as unknown[]).length ? <details className="mt-1"><summary className="cursor-pointer text-[12px] text-blue">{t("toolCalls")}（{(tk.tool_calls as unknown[]).length}）</summary><pre className="mt-1 overflow-x-auto rounded-[8px] bg-surface-muted p-2 text-[11px]">{JSON.stringify(tk.tool_calls, null, 1)}</pre></details> : null}
              {tk.retrieved_sources.length ? <details className="mt-1"><summary className="cursor-pointer text-[12px] text-blue">{t("sources")}（{tk.retrieved_sources.length}）</summary><ul className="mt-1 space-y-0.5">{tk.retrieved_sources.map((s) => <li key={s.id}><a className="text-blue underline" href={s.url} target="_blank" rel="noopener noreferrer">{s.title} {s.article}</a> <span className="num text-ink-3">v{s.version}</span></li>)}</ul></details> : null}
              {tk.validation_result ? <details className="mt-1"><summary className="cursor-pointer text-[12px] text-blue">{t("validation")}</summary><pre className="mt-1 overflow-x-auto rounded-[8px] bg-surface-muted p-2 text-[11px]">{JSON.stringify(tk.validation_result, null, 1)}</pre></details> : null}
            </li>
          ))}
        </ol>
      </Card>
      {r.status !== "queued" ? <RunProgress runId={r.id} cached={r.status === "completed" || r.status === "failed"} /> : null}
    </div>
  );
}
