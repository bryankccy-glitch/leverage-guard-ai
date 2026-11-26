"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { FileText, Pause, Play, Plus, RotateCcw, Save, SkipBack, SkipForward, Sparkles, Trash2 } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useL } from "@/lib/i18n";
import { Badge, Button, Card, CardHeader, EmptyState, ErrorState, Field, LoadingBlock, Notice, NumberField, Select, SimBadge, SuccessNote } from "@/components/ui";
import { api } from "@/lib/api";
import { cn, fmtDate, fmtMoney, fmtNum } from "@/lib/format";
import { useAuth } from "@/stores/auth";
import { RunProgress } from "../agents/RunProgress";
import { MetricList } from "../common/MetricList";
import { Timeline } from "../common/Timeline";
import type { ScenarioResult } from "../common/types";

type Preset = { key: string; title_zh: string; title_en: string; trading_type: "margin" | "day_trading"; input: Record<string, unknown> };
type Step = { day: number; price: string; label?: string; action?: string; amount?: string };

export function ScenarioList() {
  const t = useTranslations();
  const locale = useLocale();
  const token = useAuth((s) => s.token);
  const presets = useQuery({ queryKey: ["presets"], queryFn: () => api<{ items: Preset[] }>("/calculate/presets", { auth: false }) });
  const sims = useQuery({ queryKey: ["simulations", token], queryFn: () => api<{ items: { id: string; scenario_name: string; scenario_type: string; status: string; rule_version_label: string; is_demo: boolean; created_at: string }[] }>("/simulations"), enabled: !!token });
  return (
    <div className="space-y-5">
      <Card>
        <CardHeader title={t("lab.choose")} desc={t("lab.subtitle")} />
        <div className="grid gap-3 p-5 sm:grid-cols-2 xl:grid-cols-4">
          {presets.isLoading ? <LoadingBlock /> : presets.data?.items.map((p, i) => (
            <Link key={p.key} href={`/scenarios/new?preset=${p.key}`} className="rounded-[12px] border border-line p-4 hover:border-brand">
              <p className="num text-[12px] text-brand">Scenario {String(i + 1).padStart(2, "0")}</p>
              <p className="mt-1 font-semibold text-ink">{locale === "en" ? p.title_en : p.title_zh}</p>
              <Badge tone={p.trading_type === "margin" ? "blue" : "brand"} className="mt-2">{p.trading_type === "margin" ? t("nav.margin") : t("nav.dayTrading")}</Badge>
            </Link>
          ))}
        </div>
      </Card>
      <Card>
        <CardHeader title={t("nav.history")} action={<Link href="/scenarios/compare" className="text-[13px] text-blue hover:underline">{t("lab.compare")}</Link>} />
        {!token ? <EmptyState title={t("common.loginToSave")} /> : sims.isLoading ? <LoadingBlock /> : sims.error ? <ErrorState error={sims.error} /> : sims.data?.items.length ? (
          <ul className="divide-y divide-line px-5 pb-3">
            {sims.data.items.map((s) => (
              <li key={s.id} className="flex flex-wrap items-center gap-3 py-3">
                <Link href={`/scenarios/${s.id}`} className="min-w-0 flex-1 font-medium text-ink hover:text-brand">{s.scenario_name}</Link>
                {s.is_demo ? <Badge tone="warning">{t("common.demo")}</Badge> : null}
                <Badge tone="unknown">{s.scenario_type}</Badge>
                <span className="num text-[12px] text-ink-3">{fmtDate(s.created_at, locale, true)}</span>
              </li>
            ))}
          </ul>
        ) : <EmptyState title={t("common.empty")} />}
      </Card>
    </div>
  );
}

export function ScenarioBuilder() {
  const t = useTranslations();
  const router = useRouter();
  const params = useSearchParams();
  const token = useAuth((s) => s.token);
  const presets = useQuery({ queryKey: ["presets"], queryFn: () => api<{ items: Preset[] }>("/calculate/presets", { auth: false }) });
  const [chosen, setPreset] = useState<Preset | null>(null);
  const [edited, setInput] = useState<Record<string, unknown> | null>(null);
  // 沒選過就用網址的 preset；沒編輯過就用預設情境的參數（衍生值，不用 effect 複製）
  const preset = chosen ?? presets.data?.items.find((x) => x.key === params.get("preset")) ?? presets.data?.items[0] ?? null;
  const input = edited ?? (preset ? (preset.input as Record<string, unknown>) : null);
  const run = useMutation({
    mutationFn: () => api<ScenarioResult>(preset!.trading_type === "margin" ? "/calculate/scenario" : "/calculate/day-trading", { body: input, auth: false }),
  });
  useEffect(() => {
    if (input && preset) run.mutate();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [preset?.key]);
  const save = useMutation({
    mutationFn: () => api<{ id: string }>("/simulations", { body: { scenario_name: preset!.title_zh, scenario_type: preset!.trading_type === "margin" ? "extreme" : "day_trading", preset_key: preset!.key, input_parameters: input } }),
    onSuccess: (r) => router.push(`/scenarios/${r.id}`),
  });
  if (!preset || !input) return <Card><LoadingBlock rows={6} /></Card>;
  const isMargin = preset.trading_type === "margin";
  const steps = (input.steps as Step[] | undefined) ?? [];
  const setField = (k: string, v: unknown) => setInput({ ...input, [k]: v });
  const setStep = (i: number, patch: Partial<Step>) => setField("steps", steps.map((s, j) => (j === i ? { ...s, ...patch } : s)));
  return (
    <div className="space-y-5">
      <div className="flex flex-wrap gap-2">
        {presets.data!.items.map((p) => (
          <button key={p.key} onClick={() => { setPreset(p); setInput(null); }} className={cn("rounded-full border px-3 py-1 text-[12px]", p.key === preset.key ? "border-brand bg-brand-soft text-brand" : "border-line text-ink-2 hover:text-ink")}>{p.title_zh}</button>
        ))}
      </div>
      <div className="grid gap-5 xl:grid-cols-[380px_minmax(0,1fr)]">
        <Card className="xl:self-start">
          <CardHeader title={t("lab.builder")} desc={preset.title_zh} action={<SimBadge />} />
          <div className="space-y-4 p-5">
            {isMargin ? (
              <>
                <div className="grid grid-cols-3 gap-2">
                  <NumberField label={t("sim.buyPrice")} value={String(input.buy_price)} onChange={(v) => setField("buy_price", v)} />
                  <NumberField label={t("sim.quantity")} value={String(input.quantity)} onChange={(v) => setField("quantity", v)} step="1" />
                  <NumberField label={t("sim.financingRatio")} value={String(input.financing_ratio)} onChange={(v) => setField("financing_ratio", v)} step="0.01" />
                </div>
                <Field label={t("lab.noticeServed")} htmlFor="notice">
                  <Select id="notice" value={String(input.notice_served ?? "same_day")} onChange={(e) => setField("notice_served", e.target.value)}>
                    <option value="same_day">{t("lab.noticeSame")}</option>
                    <option value="next_trading_day">{t("lab.noticeNext")}</option>
                    <option value="unknown">{t("lab.noticeUnknown")}</option>
                  </Select>
                </Field>
                <div className="grid grid-cols-2 gap-2">
                  <NumberField label={t("lab.unfilled")} value={String(input.unfilled_disposal_days ?? 0)} onChange={(v) => setField("unfilled_disposal_days", Number(v) || 0)} step="1" />
                  <NumberField label={t("lab.fillRatio")} value={String(input.disposal_fill_ratio ?? "1")} onChange={(v) => setField("disposal_fill_ratio", v)} step="0.1" />
                </div>
                <div>
                  <p className="mb-2 text-[13px] font-semibold text-ink-2">{t("lab.steps")}</p>
                  <ul className="space-y-2">
                    {steps.map((s, i) => (
                      <li key={i} className="grid grid-cols-[64px_1fr_1fr_32px] items-end gap-2 rounded-[10px] bg-surface-muted p-2">
                        <NumberField label={t("lab.day")} value={String(s.day)} onChange={(v) => setStep(i, { day: Number(v) || 0 })} step="1" />
                        <NumberField label={t("lab.price")} value={s.price} onChange={(v) => setStep(i, { price: v })} />
                        <Field label={t("lab.action")} htmlFor={`act-${i}`}>
                          <Select id={`act-${i}`} value={s.action ?? "none"} onChange={(e) => setStep(i, { action: e.target.value, amount: s.amount ?? "0" })}>
                            {(["none", "top_up", "add_collateral", "repay"] as const).map((a) => <option key={a} value={a}>{t(`lab.actions.${a}`)}</option>)}
                          </Select>
                        </Field>
                        <button onClick={() => setField("steps", steps.filter((_, j) => j !== i))} disabled={steps.length <= 1} aria-label={t("common.delete")} className="mb-1 grid h-8 w-8 place-items-center rounded-[8px] text-ink-3 hover:text-critical disabled:opacity-40"><Trash2 size={15} /></button>
                        {s.action && s.action !== "none" ? <div className="col-span-4"><NumberField label={t("lab.amount")} value={s.amount ?? "0"} onChange={(v) => setStep(i, { amount: v })} /></div> : null}
                      </li>
                    ))}
                  </ul>
                  <Button variant="ghost" size="sm" className="mt-2" onClick={() => setField("steps", [...steps, { day: (steps.at(-1)?.day ?? 0) + 1, price: steps.at(-1)?.price ?? "100", action: "none", amount: "0" }])}><Plus size={14} />{t("lab.addStep")}</Button>
                </div>
              </>
            ) : (
              <div className="grid grid-cols-2 gap-2">
                {(["buy_price", "buy_quantity", "sell_price", "sell_quantity", "available_cash"] as const).map((k) => (
                  <NumberField key={k} label={k} value={String(input[k] ?? "")} onChange={(v) => setField(k, v)} />
                ))}
              </div>
            )}
            {input.rule_overrides ? <Notice tone="warning">{t("lab.ruleCompare")}</Notice> : null}
            <div className="flex flex-wrap gap-2">
              <Button onClick={() => run.mutate()} disabled={run.isPending}><Play size={15} />{t("lab.run")}</Button>
              <Button variant="secondary" onClick={() => setInput(null)}><RotateCcw size={14} />{t("common.reset")}</Button>
              {token ? <Button variant="secondary" onClick={() => save.mutate()} disabled={save.isPending}><Save size={14} />{t("common.save")}</Button> : null}
            </div>
            {save.error ? <ErrorState error={save.error} /> : null}
          </div>
        </Card>
        <div className="min-w-0">
          {run.isPending ? <Card><LoadingBlock rows={8} /></Card> : run.error ? <Card><ErrorState error={run.error} onRetry={() => run.mutate()} /></Card> : run.data ? <ScenarioPlayer key={run.submittedAt} result={run.data} /> : null}
        </div>
      </div>
    </div>
  );
}

/** 情境播放：Play／Pause／Step／Reset。每一步的財務狀態與事件都來自後端推演結果。 */
export function ScenarioPlayer({ result }: { result: ScenarioResult }) {
  const t = useTranslations();
  const L = useL();
  const locale = useLocale();
  const maxStep = Math.max(...result.timeline.map((n) => n.step), 0);
  // 換一個推演結果時，父層以 key 重建元件，step 自然回到最後一步
  const [step, setStep] = useState(maxStep);
  const [playing, setPlaying] = useState(false);
  useEffect(() => {
    if (!playing) return;
    const id = setTimeout(() => {
      const next = Math.min(maxStep, step + 1);
      setStep(next);
      if (next >= maxStep) setPlaying(false);
    }, 900);
    return () => clearTimeout(id);
  }, [playing, step, maxStep]);
  const states = result.states ?? [];
  const current = states.filter((s) => s.step <= step).at(-1);
  const chartData = states.map((s) => ({ date: s.date, step: s.step, ratio: s.maintenance_ratio_pct ? Number(s.maintenance_ratio_pct) : null, price: Number(s.price) }));
  const threshold = Number(result.parameters.maintenance_threshold ?? 0) * 100;
  const disposal = states.find((s) => s.disposal)?.disposal;
  return (
    <div className="space-y-5">
      <Card>
        <div className="flex flex-wrap items-center gap-2 p-4">
          <Button size="sm" variant="secondary" onClick={() => { setStep(0); setPlaying(maxStep > 0); }} aria-label={t("lab.play")}><Play size={14} />{t("lab.play")}</Button>
          <Button size="sm" variant="secondary" onClick={() => setPlaying(false)} aria-label={t("lab.pause")}><Pause size={14} /></Button>
          <Button size="sm" variant="secondary" onClick={() => setStep((s) => Math.max(0, s - 1))} aria-label={t("lab.stepBack")}><SkipBack size={14} /></Button>
          <Button size="sm" variant="secondary" onClick={() => setStep((s) => Math.min(maxStep, s + 1))} aria-label={t("lab.stepForward")}><SkipForward size={14} /></Button>
          <Button size="sm" variant="ghost" onClick={() => { setPlaying(false); setStep(maxStep); }}><RotateCcw size={14} />{t("common.reset")}</Button>
          <span className="num ml-auto text-[13px] text-ink-2" aria-live="polite">Step {step} / {maxStep}</span>
          <SimBadge />
        </div>
        {result.trading_type === "margin" && current ? (
          <div className="grid gap-3 border-t border-line p-4 sm:grid-cols-4">
            <Mini label={t("lab.price")} value={fmtNum(current.price, locale, 2)} />
            <Mini label={t("metrics.maintenance_ratio")} value={current.maintenance_ratio_pct ? `${fmtNum(current.maintenance_ratio_pct, locale, 2)}%` : "—"} danger={current.in_margin_call} />
            <Mini label={t("metrics.financing")} value={fmtMoney(current.financing, locale)} />
            <Mini label={t("metrics.gross_pnl")} value={fmtMoney(current.metrics.gross_pnl.value, locale)} danger={Number(current.metrics.gross_pnl.value) < 0} />
          </div>
        ) : null}
      </Card>
      {result.trading_type === "margin" && chartData.length > 1 ? (
        <Card className="p-5">
          <p className="mb-2 text-[13px] font-semibold text-ink-2">{t("sim.charts.ratio")}</p>
          <div className="h-52" role="img" aria-label={chartData.map((c) => `${c.date} ${c.ratio ?? "—"}%`).join("，")}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
                <CartesianGrid stroke="var(--chart-grid)" vertical={false} />
                <XAxis dataKey="date" tick={{ fontSize: 11, fill: "var(--text-3)" }} />
                <YAxis tick={{ fontSize: 11, fill: "var(--text-3)" }} unit="%" width={46} />
                <Tooltip contentStyle={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12 }} />
                <ReferenceLine y={threshold} stroke="var(--risk-critical)" strokeDasharray="4 4" />
                <ReferenceLine x={current?.date} stroke="var(--blue)" strokeDasharray="2 3" />
                <Line dataKey="ratio" stroke="var(--chart-1)" strokeWidth={2} dot isAnimationActive={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>
      ) : null}
      {disposal && step >= maxStep ? (
        <Card>
          <CardHeader title={t("timeline.status.triggered_in_simulation") + L("：擔保品處分結算", ": collateral disposal settlement")} />
          <div className="px-5 pb-4"><MetricList metrics={disposal} highlight={["remaining_debt", "surplus_returned"]} /></div>
        </Card>
      ) : null}
      {result.trading_type === "day_trading" && result.metrics ? (
        <Card><CardHeader title={t("sim.metricsTitle")} /><div className="px-5 pb-4"><MetricList metrics={result.metrics} highlight={["net_pnl", "funding_gap"]} /></div></Card>
      ) : null}
      <Card>
        <CardHeader title={t("timeline.title")} desc={t("timeline.subtitle")} />
        <div className="p-4"><Timeline nodes={result.timeline} upTo={step} compact /></div>
      </Card>
      <Card>
        <CardHeader title={t("common.assumptions")} />
        <ul className="list-disc space-y-1 px-10 pb-5 pt-2 text-[13px] text-ink-2">{result.assumptions.map((a, i) => <li key={i}>{a}</li>)}</ul>
      </Card>
    </div>
  );
}

function Mini({ label, value, danger }: { label: string; value: string; danger?: boolean }) {
  return (
    <div className={cn("rounded-[10px] p-3", danger ? "bg-critical-soft" : "bg-surface-muted")}>
      <p className="text-[12px] text-ink-3">{label}</p>
      <p className={cn("num text-[18px] font-bold", danger ? "text-critical" : "text-ink")}>{value}</p>
    </div>
  );
}

type SimDetail = { id: string; scenario_name: string; scenario_type: string; input_parameters: Record<string, unknown>; rule_version_label: string; is_demo: boolean; results: { id: string; calculation_version: string; rule_version_label: string; created_at: string }[]; latest: null | { financial_result: Partial<ScenarioResult>; legal_result: { timeline: ScenarioResult["timeline"]; rules: ScenarioResult["rules"] }; assumptions: string[]; warnings: ScenarioResult["warnings"]; calculation_version: string; rule_version_label: string; rule_versions: Record<string, string> } };

export function ScenarioDetail({ id }: { id: string }) {
  const t = useTranslations();
  const L = useL();
  const locale = useLocale();
  const q = useQuery({ queryKey: ["simulation", id], queryFn: () => api<SimDetail>(`/simulations/${id}`) });
  const recalc = useMutation({ mutationFn: () => api(`/simulations/${id}/calculate`, { method: "POST" }), onSuccess: () => q.refetch() });
  const [run, setRun] = useState<{ run_id: string; cached: boolean } | null>(null);
  const explain = useMutation({ mutationFn: () => api<{ run_id: string; cached: boolean }>(`/simulations/${id}/explain`, { method: "POST" }), onSuccess: setRun });
  const report = useMutation({
    mutationFn: (type: "investor" | "professional") => api<{ id: string }>("/reports", { body: { run_id: run!.run_id, report_type: type } }),
  });
  const router = useRouter();
  useEffect(() => { if (report.data) router.push(`/reports/${report.data.id}`); }, [report.data, router]);
  if (q.isLoading) return <Card><LoadingBlock rows={8} /></Card>;
  if (q.error) return <Card><ErrorState error={q.error} onRetry={() => q.refetch()} /></Card>;
  const s = q.data!;
  const result: ScenarioResult | null = s.latest ? {
    trading_type: s.scenario_type === "day_trading" ? "day_trading" : "margin",
    calculation_version: s.latest.calculation_version, rule_version: s.latest.rule_version_label, rule_versions: s.latest.rule_versions,
    parameters: (s.latest.financial_result.parameters ?? {}) as Record<string, string>, opening: s.latest.financial_result.opening,
    metrics: s.latest.financial_result.metrics, states: s.latest.financial_result.states, timeline: s.latest.legal_result.timeline,
    assumptions: s.latest.assumptions, warnings: s.latest.warnings, rules: s.latest.legal_result.rules ?? [],
  } : null;
  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="text-[26px] font-bold text-ink">{s.scenario_name}</h1>
          <p className="num text-[13px] text-ink-3">{t("common.ruleVersion")} {s.rule_version_label ?? "—"} · {L(`${s.results.length} 次計算紀錄`, `${s.results.length} calculation record(s)`)} {s.is_demo ? L("· 示範情境", "· Demo scenario") : ""}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="secondary" onClick={() => recalc.mutate()} disabled={recalc.isPending}><RotateCcw size={14} />{L("以目前規則重新計算", "Recalculate with current rules")}</Button>
          <Button onClick={() => explain.mutate()} disabled={explain.isPending}><Sparkles size={15} />{t("sim.analyze")}</Button>
        </div>
      </div>
      {recalc.isSuccess ? <SuccessNote>{L("已新增一筆計算紀錄；舊紀錄保留不變。", "A new calculation record was added; earlier records are kept unchanged.")}</SuccessNote> : null}
      {explain.error ? <ErrorState error={explain.error} /> : null}
      {run ? (
        <>
          <RunProgress key={run.run_id} runId={run.run_id} cached={run.cached} />
          <div className="flex flex-wrap gap-2">
            <Button variant="secondary" onClick={() => report.mutate("investor")} disabled={report.isPending}><FileText size={14} />{t("reports.create")}（{t("reports.investor")}）</Button>
            <Button variant="secondary" onClick={() => report.mutate("professional")} disabled={report.isPending}><FileText size={14} />{t("reports.create")}（{t("reports.professional")}）</Button>
          </div>
          {report.error ? <ErrorState error={report.error} /> : null}
        </>
      ) : null}
      {result ? <ScenarioPlayer key={`${s.results.length}-${s.latest?.rule_version_label}`} result={result} /> : <Card><EmptyState title={L("尚未計算", "Not calculated yet")} action={<Button onClick={() => recalc.mutate()}>{L("計算", "Calculate")}</Button>} /></Card>}
      <Card>
        <CardHeader title={L("計算紀錄（不可覆寫）", "Calculation records (immutable)")} />
        <ul className="divide-y divide-line px-5 pb-3 text-[13px]">
          {s.results.map((r) => (
            <li key={r.id} className="num flex flex-wrap gap-3 py-2 text-ink-2"><span>{fmtDate(r.created_at, locale, true)}</span><span>{r.calculation_version}</span><span>{r.rule_version_label}</span></li>
          ))}
        </ul>
      </Card>
    </div>
  );
}

export function ScenarioCompare() {
  const t = useTranslations();
  const locale = useLocale();
  const token = useAuth((s) => s.token);
  const sims = useQuery({ queryKey: ["simulations", token], queryFn: () => api<{ items: { id: string; scenario_name: string; scenario_type: string }[] }>("/simulations"), enabled: !!token });
  const [picked, setPicked] = useState<string[]>([]);
  const [ruleCompare, setRuleCompare] = useState(false);
  const cmp = useMutation({
    mutationFn: () => api<{ items: { id: string; name: string; result: SimDetail["latest"] & { rule_version_label: string } }[] }>(`/simulations/${picked[0]}/compare`, { body: { other_ids: picked.slice(1), rule_overrides: ruleCompare ? { "MARGIN-CALL-THRESHOLD": "9.0.0-demo" } : null } }),
  });
  if (!token) return <Card><EmptyState title={t("common.loginToSave")} /></Card>;
  return (
    <div className="space-y-5">
      <Card>
        <CardHeader title={t("lab.compare")} desc={t("lab.compareDesc")} />
        <div className="space-y-3 p-5">
          {sims.isLoading ? <LoadingBlock /> : (
            <ul className="grid gap-2 md:grid-cols-2">
              {sims.data?.items.map((s) => (
                <li key={s.id}>
                  <label className="flex cursor-pointer items-center gap-2 rounded-[10px] border border-line px-3 py-2 text-[14px] hover:bg-surface-muted">
                    <input type="checkbox" checked={picked.includes(s.id)} onChange={(e) => setPicked((p) => (e.target.checked ? [...p, s.id] : p.filter((x) => x !== s.id)))} />
                    {s.scenario_name}
                  </label>
                </li>
              ))}
            </ul>
          )}
          <label className="flex items-center gap-2 text-[14px] text-ink-2"><input type="checkbox" checked={ruleCompare} onChange={(e) => setRuleCompare(e.target.checked)} />{t("lab.ruleCompare")}</label>
          <Button onClick={() => cmp.mutate()} disabled={!picked.length || cmp.isPending}>{t("lab.compare")}</Button>
          {cmp.error ? <ErrorState error={cmp.error} /> : null}
        </div>
      </Card>
      {cmp.data ? (
        <div className="grid gap-4" style={{ gridTemplateColumns: `repeat(${Math.min(cmp.data.items.length, 3)}, minmax(0, 1fr))` }}>
          {cmp.data.items.map((it) => {
            const states = it.result?.financial_result.states ?? [];
            const last = states.at(-1);
            const events = (it.result?.legal_result.timeline ?? []).filter((n) => n.event_type !== "price_change");
            return (
              <Card key={it.id} className="p-4">
                <p className="font-semibold text-ink">{it.name}</p>
                <p className="num text-[12px] text-ink-3">{it.result?.rule_version_label}</p>
                {last ? <p className="num mt-2 text-[13px] text-ink-2">{locale === "en" ? `Last price ${last.price} / ratio ${last.maintenance_ratio_pct ?? "—"}% / P&L before costs ${fmtMoney(last.metrics.gross_pnl.value, locale)}` : `最後價格 ${last.price}／維持率 ${last.maintenance_ratio_pct ?? "—"}%／未計費用損益 ${fmtMoney(last.metrics.gross_pnl.value, locale)}`}</p> : null}
                <ul className="mt-3 space-y-1.5 text-[13px]">
                  {events.map((n) => <li key={n.id} className="flex items-center justify-between gap-2"><span className="truncate">{n.title_zh}</span><span className="num text-[11px] text-ink-3">{n.date ?? "—"}</span></li>)}
                </ul>
              </Card>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}
