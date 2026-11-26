"use client";

import { keepPreviousData, useMutation, useQuery } from "@tanstack/react-query";
import { Save, Sparkles } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { useEffect, useMemo, useState } from "react";
import { demoSwap, useIsEn, useL } from "@/lib/i18n";
import { Badge, Button, Card, CardHeader, ErrorState, Field, Input, LoadingBlock, Notice, NumberField, Select, SimBadge, SuccessNote } from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import { nextWeekday, useToday } from "@/lib/format";
import { useAuth } from "@/stores/auth";
import { RunProgress } from "../agents/RunProgress";
import { MetricList } from "../common/MetricList";
import { Timeline } from "../common/Timeline";
import type { ScenarioResult } from "../common/types";
import { Copilot } from "../copilot/Copilot";

type In = {
  asset_label: string; direction: "buy_first" | "sell_first"; buy_price: string; buy_quantity: string; sell_price: string;
  sell_quantity: string; trade_date: string; available_cash: string; assumed_buyback_price: string; assumed_borrow_fee_rate: string;
  fee_rate: string; fee_discount: string; min_fee: string;
};

const BASE: In = {
  asset_label: "示範股票（虛構）", direction: "buy_first", buy_price: "100", buy_quantity: "1000", sell_price: "102", sell_quantity: "1000",
  trade_date: "", available_cash: "50000", assumed_buyback_price: "", assumed_borrow_fee_rate: "", fee_rate: "0.001425", fee_discount: "1", min_fee: "20",
};

const SCENARIOS: { key: string; patch: Partial<In> }[] = [
  { key: "scenarioA", patch: { direction: "buy_first", buy_quantity: "1000", sell_quantity: "1000", sell_price: "102", available_cash: "50000" } },
  { key: "scenarioB", patch: { direction: "buy_first", buy_quantity: "2000", sell_quantity: "0", sell_price: "98", available_cash: "50000" } },
  { key: "scenarioC", patch: { direction: "sell_first", buy_quantity: "1000", sell_quantity: "2000", sell_price: "102", assumed_buyback_price: "104", assumed_borrow_fee_rate: "0.02" } },
  { key: "scenarioD", patch: { direction: "buy_first", buy_quantity: "2000", sell_quantity: "1000", sell_price: "102", available_cash: "50000" } },
  { key: "scenarioE", patch: { direction: "buy_first", buy_quantity: "3000", sell_quantity: "1000", sell_price: "97", available_cash: "20000" } },
];

export function DayTradeSimulator() {
  const t = useTranslations();
  const L = useL();
  const token = useAuth((s) => s.token);
  const [inpState, setInp] = useState<In>(BASE);
  const today = useToday();
  const isEn = useIsEn();
  const inp = useMemo(() => {
    const v = inpState.trade_date || !today ? inpState : { ...inpState, trade_date: nextWeekday(today) };
    return { ...v, asset_label: demoSwap(v.asset_label, isEn) };
  }, [inpState, today, isEn]);
  const set = (k: keyof In) => (v: string) => setInp({ ...inp, [k]: v });
  const [debounced, setDebounced] = useState(inp);
  useEffect(() => {
    const id = setTimeout(() => setDebounced(inp), 300);
    return () => clearTimeout(id);
  }, [inp]);
  const body = useMemo(() => ({
    asset_label: debounced.asset_label, direction: debounced.direction, buy_price: debounced.buy_price, buy_quantity: debounced.buy_quantity || "0",
    sell_price: debounced.sell_price, sell_quantity: debounced.sell_quantity || "0", trade_date: debounced.trade_date, available_cash: debounced.available_cash || "0",
    assumed_buyback_price: debounced.assumed_buyback_price || null, assumed_borrow_fee_rate: debounced.assumed_borrow_fee_rate || null,
    fees: { fee_rate: debounced.fee_rate, fee_discount: debounced.fee_discount, min_fee: debounced.min_fee },
  }), [debounced]);
  const calc = useQuery({
    queryKey: ["dt-calc", body],
    queryFn: ({ signal }) => api<ScenarioResult>("/calculate/day-trading", { body, auth: false, signal }),
    enabled: !!body.trade_date,
    placeholderData: keepPreviousData,
    retry: 0,
  });
  const d = calc.data;
  const err = (f: string) => (calc.error instanceof ApiError ? calc.error.fieldErrors.find((e) => e.field === f)?.message : undefined);
  const [saved, setSaved] = useState<string | null>(null);
  const [run, setRun] = useState<{ run_id: string; cached: boolean } | null>(null);
  const save = useMutation({
    mutationFn: () => api<{ id: string }>("/simulations", { body: { scenario_name: isEn ? `Day-trade simulation: ${inp.asset_label} (${inp.direction === "buy_first" ? "buy first" : "sell first"})` : `當沖模擬：${inp.asset_label}（${inp.direction === "buy_first" ? "先買後賣" : "先賣後買"}）`, scenario_type: "day_trading", input_parameters: body } }),
    onSuccess: (r) => setSaved(r.id),
  });
  const analyze = useMutation({
    mutationFn: async () => {
      const id = saved ?? (await save.mutateAsync()).id;
      return api<{ run_id: string; cached: boolean }>(`/simulations/${id}/explain`, { method: "POST" });
    },
    onSuccess: setRun,
  });

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap gap-2" role="group" aria-label={t("sim.presets")}>
        {SCENARIOS.map((s) => (
          <button key={s.key} onClick={() => setInp({ ...inp, ...s.patch })} className="rounded-full border border-line bg-surface px-3 py-1.5 text-[13px] text-ink-2 hover:border-brand hover:text-ink">
            {t(`sim.dt.${s.key}`)}
          </button>
        ))}
      </div>
      <div className="grid gap-5 xl:grid-cols-[320px_minmax(0,1fr)_380px]">
        <Card className="xl:self-start">
          <CardHeader title={t("sim.controls")} action={<SimBadge />} />
          <div className="space-y-4 p-5">
            <Field label={t("sim.asset")} htmlFor="dt-asset"><Input id="dt-asset" value={inp.asset_label} onChange={(e) => set("asset_label")(e.target.value)} maxLength={60} /></Field>
            <Field label={t("sim.dt.direction")} htmlFor="dt-dir">
              <Select id="dt-dir" value={inp.direction} onChange={(e) => set("direction")(e.target.value)}>
                <option value="buy_first">{t("sim.dt.buyFirst")}</option>
                <option value="sell_first">{t("sim.dt.sellFirst")}</option>
              </Select>
            </Field>
            <div className="grid grid-cols-2 gap-3">
              <NumberField label={t("sim.dt.buyPrice")} value={inp.buy_price} onChange={set("buy_price")} error={err("buy_price")} />
              <NumberField label={t("sim.dt.buyQty")} value={inp.buy_quantity} onChange={set("buy_quantity")} step="1" error={err("buy_quantity")} />
              <NumberField label={t("sim.dt.sellPrice")} value={inp.sell_price} onChange={set("sell_price")} error={err("sell_price")} />
              <NumberField label={t("sim.dt.sellQty")} value={inp.sell_quantity} onChange={set("sell_quantity")} step="1" error={err("sell_quantity")} />
            </div>
            <Field label={t("sim.dt.tradeDate")} htmlFor="dt-date"><Input id="dt-date" type="date" value={inp.trade_date} onChange={(e) => set("trade_date")(e.target.value)} /></Field>
            <NumberField label={t("sim.dt.cash")} value={inp.available_cash} onChange={set("available_cash")} />
            {inp.direction === "sell_first" ? (
              <div className="grid grid-cols-2 gap-3 rounded-[12px] bg-surface-muted p-3">
                <NumberField label={t("sim.dt.buyback")} value={inp.assumed_buyback_price} onChange={set("assumed_buyback_price")} />
                <NumberField label={t("sim.dt.borrowFee")} value={inp.assumed_borrow_fee_rate} onChange={set("assumed_borrow_fee_rate")} hint={L("上限 0.07（收盤價 7%）", "Max 0.07 (7% of closing price)")} error={err("assumed_borrow_fee_rate")} />
              </div>
            ) : null}
            <details className="rounded-[8px] border border-line px-3 py-2">
              <summary className="cursor-pointer text-[13px] text-ink-2">{t("sim.feeRate")}</summary>
              <div className="mt-3 grid grid-cols-3 gap-2">
                <NumberField label={t("sim.feeRate")} value={inp.fee_rate} onChange={set("fee_rate")} />
                <NumberField label={t("sim.feeDiscount")} value={inp.fee_discount} onChange={set("fee_discount")} />
                <NumberField label={t("sim.minFee")} value={inp.min_fee} onChange={set("min_fee")} />
              </div>
            </details>
            {token ? <Button variant="secondary" size="sm" onClick={() => save.mutate()} disabled={save.isPending}><Save size={14} />{t("sim.saveScenario")}</Button> : <Link href="/login" className="text-[12px] text-blue hover:underline">{t("common.loginToSave")}</Link>}
            {saved ? <SuccessNote><Link className="underline" href={`/scenarios/${saved}`}>{L("已儲存情境", "Scenario saved")}</Link></SuccessNote> : null}
          </div>
        </Card>

        <div className="min-w-0 space-y-5">
          {calc.error && !d ? <Card><ErrorState error={calc.error} onRetry={() => calc.refetch()} /></Card> : calc.isLoading || !d ? <Card><LoadingBlock rows={8} /></Card> : (
            <>
              <div className="flex flex-wrap items-center gap-2 text-[12px]">
                <Badge tone="blue">{isEn ? `Tax ${Number(d.parameters.day_trade_tax_rate) * 1000}‰ (day trade) / ${Number(d.parameters.general_tax_rate) * 1000}‰ (general)` : `稅率 ${Number(d.parameters.day_trade_tax_rate) * 1000}‰（當沖）／${Number(d.parameters.general_tax_rate) * 1000}‰（一般）`}</Badge>
                <Badge tone="unknown">{L("交割日", "Settlement date")} {d.parameters.settlement_date}</Badge>
                <span className="num text-ink-3">{t("common.ruleVersion")} {d.rule_version}</span>
              </div>
              <Card>
                <CardHeader title={t("sim.metricsTitle")} desc={L("點一下任一數字可以看公式", "Click any number to see its formula")} />
                <div className="px-5 pb-4">
                  <MetricList metrics={d.metrics!} highlight={["net_pnl", "funding_gap", "settlement_payable"]} />
                </div>
              </Card>
              {d.warnings.length ? (
                <Notice tone="warning" title={t("sim.warnings")}>
                  <ul className="list-disc pl-5">{d.warnings.map((w) => <li key={w.code}>{w.message}</li>)}</ul>
                </Notice>
              ) : null}
              {Number(d.metrics?.funding_gap.value) > 0 ? <Notice tone="blue">{t("sim.dt.gapNote")}</Notice> : null}
              <Card>
                <CardHeader title={t("common.assumptions")} />
                <ul className="list-disc space-y-1 px-10 pb-5 pt-2 text-[13px] text-ink-2">{d.assumptions.map((a, i) => <li key={i}>{a}</li>)}</ul>
              </Card>
            </>
          )}
        </div>

        <div className="space-y-5">
          <Card>
            <CardHeader title={t("timeline.title")} desc={t("timeline.subtitle")} />
            <div className="p-4">{d ? <Timeline nodes={d.timeline} /> : <LoadingBlock />}</div>
          </Card>
          {token ? <Button onClick={() => analyze.mutate()} disabled={analyze.isPending || !d}><Sparkles size={15} />{analyze.isPending ? t("sim.analyzing") : t("sim.analyze")}</Button> : null}
          {analyze.error ? <ErrorState error={analyze.error} /> : null}
          {run ? <RunProgress key={run.run_id} runId={run.run_id} cached={run.cached} /> : null}
        </div>
      </div>
      <Copilot context={{ trading_type: "day_trading", input: body }} />
    </div>
  );
}
