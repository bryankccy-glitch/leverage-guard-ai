"use client";

import { useMutation } from "@tanstack/react-query";
import { Plus, Trash2 } from "lucide-react";
import { useState } from "react";
import { demoSwap, useIsEn, useL } from "@/lib/i18n";
import { Button, Card, CardHeader, ErrorState, Input, Notice, NumberField, PageHeader, SimBadge } from "@/components/ui";
import { api } from "@/lib/api";
import { MetricList } from "../common/MetricList";
import type { Metric } from "../common/types";

type Pos = { label: string; quantity: string; simulated_price: string; financing_principal: string };

export function PortfolioCalc() {
  const [pos, setPos] = useState<Pos[]>([
    { label: "示範股票 A（虛構）", quantity: "1000", simulated_price: "100", financing_principal: "60000" },
    { label: "示範股票 B（虛構）", quantity: "1000", simulated_price: "30", financing_principal: "30000" },
  ]);
  const isEn = useIsEn();
  const L = useL();
  const shown = pos.map((p) => ({ ...p, label: demoSwap(p.label, isEn) }));
  const [col, setCol] = useState("0");
  const m = useMutation({ mutationFn: () => api<{ metrics: Record<string, Metric>; limitations: string[] }>("/calculate/portfolio", { body: { positions: shown.map((p) => ({ ...p, label: p.label || L("部位", "Position") })), collateral_value: col }, auth: false }) });
  const set = (i: number, k: keyof Pos, v: string) => setPos((ps) => ps.map((p, j) => (j === i ? { ...p, [k]: v } : p)));
  return (
    <>
      <PageHeader title={L("整戶維持率試算", "Account-level maintenance ratio")} subtitle={L("整戶維持率是把各部位市值與融資金額分別加總後相除，不能把各部位的維持率直接平均（操作辦法第 53 條）。", "The account-level ratio sums market values and margin loans across positions and then divides; it is not an average of each position's ratio (operating rules Art. 53).")} badge={<SimBadge />} />
      <div className="grid gap-5 lg:grid-cols-2">
        <Card>
          <CardHeader title={L("融資部位", "Margin positions")} />
          <div className="space-y-3 p-5">
            {shown.map((p, i) => (
              <div key={i} className="grid grid-cols-[1fr_1fr_1fr_32px] items-end gap-2 rounded-[10px] bg-surface-muted p-2">
                <div className="col-span-4"><Input aria-label={L("名稱", "Name")} value={p.label} onChange={(e) => set(i, "label", e.target.value)} /></div>
                <NumberField label={L("股數", "Shares")} value={p.quantity} onChange={(v) => set(i, "quantity", v)} step="1" />
                <NumberField label={L("模擬價格", "Simulated price")} value={p.simulated_price} onChange={(v) => set(i, "simulated_price", v)} />
                <NumberField label={L("融資金額", "Margin loan")} value={p.financing_principal} onChange={(v) => set(i, "financing_principal", v)} />
                <button aria-label={L("刪除", "Delete")} disabled={pos.length <= 1} onClick={() => setPos(pos.filter((_, j) => j !== i))} className="mb-1 grid h-8 w-8 place-items-center rounded-[8px] text-ink-3 hover:text-critical disabled:opacity-40"><Trash2 size={15} /></button>
              </div>
            ))}
            <Button variant="ghost" size="sm" onClick={() => setPos([...pos, { label: "", quantity: "1000", simulated_price: "50", financing_principal: "30000" }])}><Plus size={14} />{L("新增部位", "Add position")}</Button>
            <NumberField label={L("抵繳品市值（已折算）", "Substitute collateral value (discounted)")} value={col} onChange={setCol} />
            <Button onClick={() => m.mutate()} disabled={m.isPending}>{L("計算整戶維持率", "Calculate account ratio")}</Button>
          </div>
        </Card>
        <Card>
          <CardHeader title={L("結果", "Result")} />
          <div className="px-5 pb-5">
            {m.error ? <ErrorState error={m.error} /> : m.data ? (
              <>
                <MetricList metrics={m.data.metrics} highlight={["account_maintenance_ratio"]} />
                <Notice tone="unknown">{m.data.limitations.join("；")}</Notice>
              </>
            ) : <p className="py-6 text-[13px] text-ink-3">{L("輸入部位後按「計算」。", "Enter positions, then press Calculate.")}</p>}
          </div>
        </Card>
      </div>
    </>
  );
}
