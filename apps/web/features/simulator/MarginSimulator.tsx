"use client";

import * as Slider from "@radix-ui/react-slider";
import { keepPreviousData, useMutation, useQuery } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle2, Info, RotateCcw, Save, Sparkles } from "lucide-react";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { useEffect, useMemo, useState } from "react";
import { Badge, Button, Card, CardHeader, ErrorState, Field, Input, LoadingBlock, Notice, NumberField, SimBadge, SuccessNote } from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import { cn, fmtMoney, fmtNum, nextWeekday, todayTW, useToday } from "@/lib/format";
import { marginPreview } from "@/lib/margin-preview";
import { useAuth } from "@/stores/auth";
import { RunProgress } from "../agents/RunProgress";
import { MetricList } from "../common/MetricList";
import { CitationItem } from "../common/Timeline";
import type { MarginCalcResult } from "../common/types";
import { Copilot } from "../copilot/Copilot";
import { MarginCharts } from "./MarginCharts";

type Inputs = {
  asset_label: string;
  buy_price: string;
  quantity: string;
  financing_ratio: string;
  current_price: string;
  annual_interest_rate: string;
  holding_days: string;
  fee_rate: string;
  fee_discount: string;
  min_fee: string;
  other_collateral_value: string;
  as_of: string;
};

const DEFAULTS: Inputs = {
  asset_label: "示範股票（虛構）", buy_price: "100", quantity: "1000", financing_ratio: "0.6", current_price: "100",
  annual_interest_rate: "0.0645", holding_days: "30", fee_rate: "0.001425", fee_discount: "1", min_fee: "20",
  other_collateral_value: "0", as_of: "",
};

const PRESETS: { key: string; label: string; price: string }[] = [
  { key: "flat", label: "持平 100", price: "100" },
  { key: "m20", label: "−20%（80）", price: "80" },
  { key: "m30", label: "−30%（70）", price: "70" },
  { key: "m50", label: "−50%（50）", price: "50" },
];

function useDebounced<T>(v: T, ms = 300) {
  const [d, setD] = useState(v);
  useEffect(() => {
    const id = setTimeout(() => setD(v), ms);
    return () => clearTimeout(id);
  }, [v, ms]);
  return d;
}

export function MarginSimulator() {
  const t = useTranslations();
  const locale = useLocale();
  const token = useAuth((s) => s.token);
  const [inpState, setInp] = useState<Inputs>(DEFAULTS);
  // 日期只在瀏覽器端取得（預先渲染時不能讀取目前時間）
  const today = useToday();
  const inp = useMemo(() => (inpState.as_of || !today ? inpState : { ...inpState, as_of: today }), [inpState, today]);
  const set = (k: keyof Inputs) => (v: string) => setInp({ ...inp, [k]: v });
  const debounced = useDebounced(inp);

  const body = useMemo(() => ({
    asset_label: debounced.asset_label || "模擬資產",
    buy_price: debounced.buy_price, quantity: debounced.quantity, financing_ratio: debounced.financing_ratio,
    current_price: debounced.current_price, annual_interest_rate: debounced.annual_interest_rate || null,
    holding_days: Number(debounced.holding_days || 0), other_collateral_value: debounced.other_collateral_value || "0",
    fees: { fee_rate: debounced.fee_rate, fee_discount: debounced.fee_discount, min_fee: debounced.min_fee },
    as_of: debounced.as_of || null, curve: true,
  }), [debounced]);

  const calc = useQuery({
    queryKey: ["margin-calc", body],
    queryFn: ({ signal }) => api<MarginCalcResult>("/calculate/margin", { body, auth: false, signal }),
    placeholderData: keepPreviousData,
    retry: 0,
  });
  const data = calc.data;
  const thresholdParam = data?.rules.find((r) => r.rule_id === "MARGIN-CALL-THRESHOLD")?.parameters.threshold ?? "1.30";
  const cancelParam = data?.rules.find((r) => r.rule_id === "MARGIN-CALL-CANCEL")?.parameters.cancel_threshold;
  const preview = marginPreview({ buyPrice: inp.buy_price, quantity: inp.quantity, financingRatio: inp.financing_ratio, currentPrice: inp.current_price, threshold: thresholdParam, otherCollateral: inp.other_collateral_value });
  const fieldErr = (f: string) => (calc.error instanceof ApiError ? calc.error.fieldErrors.find((e) => e.field === f || e.field.endsWith(`.${f}`))?.message : undefined);
  const stale = JSON.stringify(inp) !== JSON.stringify(debounced) || calc.isFetching;
  const backendRatio = data?.metrics.maintenance_ratio?.value;
  const mismatch = !stale && preview && backendRatio && preview.ratioPct !== backendRatio;

  const buy = Number(inp.buy_price) || 100;
  const minP = Math.max(0.01, +(buy * 0.3).toFixed(2));
  const maxP = +(buy * 1.3).toFixed(2);
  const curP = Number(inp.current_price) || buy;

  const [saved, setSaved] = useState<string | null>(null);
  const [run, setRun] = useState<{ run_id: string; cached: boolean } | null>(null);
  const scenarioInput = () => ({
    asset_label: inp.asset_label, buy_price: inp.buy_price, quantity: inp.quantity, financing_ratio: inp.financing_ratio,
    annual_interest_rate: inp.annual_interest_rate || null, start_date: nextWeekday(inp.as_of || todayTW()),
    fees: { fee_rate: inp.fee_rate, fee_discount: inp.fee_discount, min_fee: inp.min_fee },
    other_collateral_value: inp.other_collateral_value || "0",
    steps: [{ day: 0, price: inp.buy_price, label: "建倉" }, { day: 1, price: inp.current_price, label: "模擬價格" }],
  });
  const save = useMutation({
    mutationFn: () => api<{ id: string }>("/simulations", { body: { scenario_name: `融資模擬：${inp.asset_label} @ ${inp.current_price}`, scenario_type: "margin", input_parameters: scenarioInput() } }),
    onSuccess: (r) => setSaved(r.id),
  });
  const analyze = useMutation({
    mutationFn: async () => {
      const id = saved ?? (await save.mutateAsync()).id;
      return api<{ run_id: string; cached: boolean }>(`/simulations/${id}/explain`, { method: "POST" });
    },
    onSuccess: setRun,
  });

  // 單一價格試算只判斷「是否跌破門檻」；取消追繳、處分等事件需要時間序列，交給情境實驗室
  const SINGLE_POINT_RULES = ["MARGIN-CALL-THRESHOLD"];
  const rulesWithEvents = data?.rules.filter((r) => SINGLE_POINT_RULES.includes(r.rule_id) && data.rule_evaluation.matched.includes(r.rule_id)) ?? [];
  const triggered = rulesWithEvents.map((r) => r.rule_id);

  return (
    <div className="space-y-5">
      <div className="grid gap-5 xl:grid-cols-[320px_minmax(0,1fr)_380px]">
        {/* 左欄：參數 */}
        <Card className="xl:sticky xl:top-24 xl:self-start">
          <CardHeader title={t("sim.controls")} action={<SimBadge />} />
          <div className="space-y-4 p-5">
            <Field label={t("sim.asset")} htmlFor="asset"><Input id="asset" value={inp.asset_label} maxLength={60} onChange={(e) => set("asset_label")(e.target.value)} /></Field>
            <div className="grid grid-cols-2 gap-3">
              <NumberField label={t("sim.buyPrice")} value={inp.buy_price} onChange={set("buy_price")} error={fieldErr("buy_price")} />
              <NumberField label={t("sim.quantity")} value={inp.quantity} onChange={set("quantity")} step="1" error={fieldErr("quantity")} suffix={t("common.shares")} />
            </div>
            <NumberField label={t("sim.financingRatio")} value={inp.financing_ratio} onChange={set("financing_ratio")} step="0.01" error={fieldErr("financing_ratio")} hint="0.6 = 六成（依標的與券商規定）" />
            <div className="space-y-2 rounded-[12px] bg-surface-muted p-3">
              <div className="flex items-baseline justify-between">
                <label htmlFor="price-slider" className="text-[13px] font-medium text-ink-2">{t("sim.currentPrice")}</label>
                <span className={cn("num text-[20px] font-bold", curP < buy ? "text-down" : curP > buy ? "text-up" : "text-ink")}>{fmtNum(inp.current_price, locale, 2)}</span>
              </div>
              <Slider.Root id="price-slider" className="relative flex h-6 w-full touch-none select-none items-center" min={minP} max={maxP} step={0.5} value={[Math.min(Math.max(curP, minP), maxP)]} onValueChange={([v]) => set("current_price")(String(v))} aria-label={t("sim.currentPrice")}>
                <Slider.Track className="relative h-1.5 grow rounded-full bg-line"><Slider.Range className="absolute h-full rounded-full bg-brand" /></Slider.Track>
                <Slider.Thumb aria-label={t("sim.currentPrice")} className="block h-5 w-5 rounded-full border-2 border-brand bg-surface shadow" />
              </Slider.Root>
              <div className="flex flex-wrap gap-1.5">
                {PRESETS.map((p) => (
                  <button key={p.key} onClick={() => set("current_price")(String((buy * Number(p.price)) / 100))} className="rounded-full border border-line bg-surface px-2.5 py-0.5 text-[12px] text-ink-2 hover:text-ink">{p.label}</button>
                ))}
              </div>
              <p className="text-[11px] text-ink-3">價格顏色採台股慣例：紅漲綠跌（只代表價格方向，不代表風險）</p>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <NumberField label={t("sim.interestRate")} value={inp.annual_interest_rate} onChange={set("annual_interest_rate")} step="0.0001" hint="0.0645 = 6.45%" error={fieldErr("annual_interest_rate")} />
              <NumberField label={t("sim.holdingDays")} value={inp.holding_days} onChange={set("holding_days")} step="1" suffix={t("common.days")} />
            </div>
            <details className="rounded-[8px] border border-line px-3 py-2">
              <summary className="cursor-pointer text-[13px] text-ink-2">手續費、擔保品與規則日期</summary>
              <div className="mt-3 space-y-3">
                <div className="grid grid-cols-3 gap-2">
                  <NumberField label={t("sim.feeRate")} value={inp.fee_rate} onChange={set("fee_rate")} step="0.000001" />
                  <NumberField label={t("sim.feeDiscount")} value={inp.fee_discount} onChange={set("fee_discount")} step="0.01" />
                  <NumberField label={t("sim.minFee")} value={inp.min_fee} onChange={set("min_fee")} step="1" />
                </div>
                <NumberField label={t("sim.otherCollateral")} value={inp.other_collateral_value} onChange={set("other_collateral_value")} hint="抵繳品需先依規定折算（例如上市股票按基準價七折）" />
                <Field label={t("sim.asOf")} htmlFor="asof"><Input id="asof" type="date" value={inp.as_of} onChange={(e) => set("as_of")(e.target.value)} /></Field>
              </div>
            </details>
            <div className="flex flex-wrap gap-2">
              <Button variant="secondary" size="sm" onClick={() => setInp({ ...DEFAULTS, as_of: todayTW() })}><RotateCcw size={14} />{t("common.reset")}</Button>
              {token ? (
                <Button variant="secondary" size="sm" onClick={() => save.mutate()} disabled={save.isPending}><Save size={14} />{t("sim.saveScenario")}</Button>
              ) : (
                <Link href="/login" className="text-[12px] text-blue hover:underline">{t("common.loginToSave")}</Link>
              )}
            </div>
            {saved ? <SuccessNote><Link href={`/scenarios/${saved}`} className="underline">已儲存情境</Link></SuccessNote> : null}
            {save.error ? <ErrorState error={save.error} /> : null}
          </div>
        </Card>

        {/* 中欄：財務視覺化 */}
        <div className="min-w-0 space-y-5">
          <div className="grid grid-cols-2 gap-3 2xl:grid-cols-4">
            <Kpi hero label={t("metrics.maintenance_ratio")} value={preview?.ratioPct ? `${fmtNum(preview.ratioPct, locale, 2)}%` : "—"} sub={preview?.belowThreshold ? `低於 ${Number(thresholdParam) * 100}% 門檻` : `門檻 ${Number(thresholdParam) * 100}%`} warn={preview?.belowThreshold} />
            <Kpi label={t("metrics.gross_pnl")} value={preview ? fmtMoney(preview.grossPnl, locale) : "—"} negative={preview?.grossPnl.startsWith("-")} />
            <Kpi label={t("metrics.threshold_price")} value={preview?.thresholdPrice ? fmtNum(preview.thresholdPrice, locale, 2) : "—"} sub={t("common.simplified")} />
            <Kpi label={t("metrics.margin_call_amount")} value={preview ? fmtMoney(preview.callAmount, locale) : "—"} sub="依第 54 條公式" />
          </div>
          <div className="flex flex-wrap items-center gap-2 text-[12px]" aria-live="polite">
            <Badge tone="blue">{t("sim.previewCalc")}：Decimal.js</Badge>
            {stale ? <Badge tone="unknown">{t("sim.calcPending")}</Badge> : data ? <Badge tone="normal" icon={<CheckCircle2 size={12} aria-hidden />}>{t("sim.officialCalc")} {data.calculation_version}</Badge> : null}
            {mismatch ? <Badge tone="warning">{t("sim.calcMismatch")}</Badge> : null}
            {data ? <span className="num text-ink-3">{t("common.ruleVersion")} {data.rule_version}</span> : null}
          </div>
          <Card>
            <CardHeader title={t("sim.visual")} desc={t("sim.thresholdNote")} />
            <div className="p-5">
              {calc.isLoading ? <LoadingBlock rows={6} /> : calc.error && !data ? <ErrorState error={calc.error} onRetry={() => calc.refetch()} /> : data?.curve ? (
                <MarginCharts curve={data.curve} currentPrice={curP} threshold={Number(thresholdParam) * 100} cancel={cancelParam ? Number(cancelParam) * 100 : null} thresholdPrice={preview?.thresholdPrice ? Number(preview.thresholdPrice) : null} />
              ) : null}
            </div>
          </Card>
          <Card>
            <CardHeader title={t("sim.metricsTitle")} desc="點一下任一數字可以看公式、輸入與規則" />
            <div className="px-5 pb-4">
              {data ? <MetricList metrics={data.metrics} highlight={["maintenance_ratio", "net_pnl", "margin_call_amount"]} /> : <LoadingBlock rows={8} />}
            </div>
          </Card>
          {data ? (
            <Card>
              <CardHeader title={t("common.assumptions")} />
              <ul className="list-disc space-y-1 px-10 pb-5 pt-2 text-[13px] text-ink-2">
                {data.assumptions.map((a, i) => <li key={i}>{a}</li>)}
                {data.warnings.map((w) => <li key={w.code} className="text-warning">{w.message}</li>)}
              </ul>
            </Card>
          ) : null}
        </div>

        {/* 右欄：法律後果 */}
        <div className="space-y-5">
          <Card>
            <CardHeader title={t("sim.legal")} desc={`${t("sim.triggered")}：${triggered.length}`} />
            <div className="space-y-3 p-5">
              {triggered.length === 0 ? (
                <Notice tone="normal" title={t("sim.notTriggered")}>
                  目前模擬價格下，維持率高於追繳門檻。這不代表交易安全：股價繼續變動，事件仍可能觸發。
                </Notice>
              ) : (
                rulesWithEvents.map((r) => (
                  <div key={r.rule_id} className="rounded-[12px] border border-critical/30 bg-critical-soft p-3">
                    <p className="flex items-center gap-2 font-semibold text-critical"><AlertTriangle size={15} aria-hidden />{r.rule_name}</p>
                    <p className="mt-1 text-[13px] text-ink">{r.plain_language}</p>
                    <ul className="mt-2 space-y-1.5">{r.citations.map((c, i) => <CitationItem key={i} c={c} />)}</ul>
                  </div>
                ))
              )}
              {triggered.length ? (
                <Notice tone="warning" title="接下來可能發生">
                  補繳期限從「通知送達之日」起算二個營業日；期限內沒補足、期限當天維持率仍不足，券商自次一營業日起處分擔保品。
                  <Link href="/scenarios/new?preset=residual_debt" className="ml-1 text-blue underline">在實驗室推演完整時間軸</Link>
                </Notice>
              ) : null}
              <div className="flex flex-wrap gap-2">
                {token ? (
                  <Button onClick={() => analyze.mutate()} disabled={analyze.isPending}><Sparkles size={15} />{analyze.isPending ? t("sim.analyzing") : t("sim.analyze")}</Button>
                ) : (
                  <Notice tone="blue">{t("dashboard.loginPrompt")} <Link href="/login" className="text-blue underline">{t("shell.login")}</Link></Notice>
                )}
              </div>
              {analyze.error ? <ErrorState error={analyze.error} /> : null}
            </div>
          </Card>
          {run ? <RunProgress key={run.run_id} runId={run.run_id} cached={run.cached} /> : null}
          <Card>
            <CardHeader title={t("sim.rulesUsed")} desc={data?.rules.some((r) => r.review_status === "pending_review") ? t("common.unreviewed") : data?.rules.some((r) => r.review_status === "approved") ? t("common.aiChecked") : undefined} />
            <ul className="space-y-2 p-5 text-[13px]">
              {data?.rules.filter((r) => r.has_official_source).map((r) => (
                <li key={r.rule_id} className="flex items-start gap-2">
                  <Info size={14} className="mt-0.5 shrink-0 text-ink-3" aria-hidden />
                  <span className="flex-1">
                    <span className="font-medium text-ink">{r.rule_name}</span>
                    <span className="num ml-1 text-[11px] text-ink-3">{r.rule_id}@{r.version}</span>
                    <span className="block text-[12px] text-ink-3">{r.citations.map((c) => `${c.official_title} ${c.article_number}`).join("、")}</span>
                  </span>
                </li>
              ))}
            </ul>
          </Card>
        </div>
      </div>
      <Copilot context={{ trading_type: "margin", input: { asset_label: inp.asset_label, buy_price: inp.buy_price, quantity: inp.quantity, financing_ratio: inp.financing_ratio, current_price: inp.current_price, annual_interest_rate: inp.annual_interest_rate || null, holding_days: Number(inp.holding_days || 0) } }} />
    </div>
  );
}

function Kpi({ label, value, sub, hero, warn, negative }: { label: string; value: string; sub?: string; hero?: boolean; warn?: boolean; negative?: boolean }) {
  return (
    <div className={cn("rounded-[12px] border p-4", hero ? (warn ? "border-critical bg-critical text-white" : "border-transparent bg-hero text-hero-fg") : "border-line bg-surface shadow-card")}>
      <p className={cn("text-[12px]", hero ? "opacity-85" : "text-ink-3")}>{label}</p>
      <p className={cn("num mt-1 text-[22px] font-bold leading-tight", !hero && negative && "text-critical")}>{value}</p>
      {sub ? <p className={cn("mt-0.5 text-[11.5px]", hero ? "opacity-85" : "text-ink-3")}>{sub}</p> : null}
    </div>
  );
}
