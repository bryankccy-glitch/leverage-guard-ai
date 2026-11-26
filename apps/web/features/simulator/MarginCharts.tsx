"use client";

import { useLocale, useTranslations } from "next-intl";
import { Area, CartesianGrid, ComposedChart, Line, LineChart, ReferenceDot, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useL } from "@/lib/i18n";
import { fmtMoney, fmtNum } from "@/lib/format";

type Pt = { price: string; maintenance_ratio: string | null; gross_pnl: string; net_pnl: string; market_value: string; financing: string };

const axis = { fontSize: 11, fill: "var(--text-3)" };

export function MarginCharts({ curve, currentPrice, threshold, cancel, thresholdPrice }: { curve: Pt[]; currentPrice: number; threshold: number; cancel: number | null; thresholdPrice: number | null }) {
  const t = useTranslations("sim.charts");
  const L = useL();
  const locale = useLocale();
  const data = curve.map((c) => ({
    price: Number(c.price),
    ratio: c.maintenance_ratio === null ? null : Number(c.maintenance_ratio),
    gross: Number(c.gross_pnl),
    net: Number(c.net_pnl),
    mv: Number(c.market_value),
    debt: Number(c.financing),
  }));
  const cur = data.reduce((best, d) => (Math.abs(d.price - currentPrice) < Math.abs(best.price - currentPrice) ? d : best), data[0]);
  return (
    <div className="space-y-5">
      <ChartBlock title={t("ratio")} summary={`${t("threshold")} ${threshold}%${thresholdPrice ? (locale === "en" ? ` (≈ ${fmtNum(thresholdPrice, locale, 2)})` : `（≈ ${fmtNum(thresholdPrice, locale, 2)}）`) : ""}`}>
        <ComposedChart data={data} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
          <CartesianGrid stroke="var(--chart-grid)" vertical={false} />
          <XAxis dataKey="price" type="number" domain={["dataMin", "dataMax"]} tick={axis} tickFormatter={(v) => fmtNum(v, locale, 0)} />
          <YAxis tick={axis} width={44} unit="%" />
          <Tooltip formatter={(v) => [`${fmtNum(String(v), locale, 2)}%`, t("ratio")]} labelFormatter={(l) => `${fmtNum(String(l), locale, 2)}`} contentStyle={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12 }} />
          <Area type="monotone" dataKey="ratio" stroke="var(--chart-1)" fill="var(--brand-soft)" strokeWidth={2} isAnimationActive={false} />
          <ReferenceLine y={threshold} stroke="var(--risk-critical)" strokeDasharray="4 4" label={{ value: `${t("threshold")} ${threshold}%`, fill: "var(--risk-critical)", fontSize: 11, position: "insideTopRight" }} />
          {cancel ? <ReferenceLine y={cancel} stroke="var(--risk-normal)" strokeDasharray="2 4" label={{ value: `${t("cancel")} ${cancel}%`, fill: "var(--risk-normal)", fontSize: 11, position: "insideTopRight" }} /> : null}
          {cur?.ratio ? <ReferenceDot x={cur.price} y={cur.ratio} r={5} fill="var(--blue)" stroke="var(--surface)" /> : null}
        </ComposedChart>
      </ChartBlock>
      <div className="grid gap-5 lg:grid-cols-2">
        <ChartBlock title={t("equity")} small>
          <LineChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid stroke="var(--chart-grid)" vertical={false} />
            <XAxis dataKey="price" type="number" domain={["dataMin", "dataMax"]} tick={axis} tickFormatter={(v) => fmtNum(v, locale, 0)} />
            <YAxis tick={axis} width={58} tickFormatter={(v) => fmtNum(v / 1000, locale, 0) + "k"} />
            <Tooltip formatter={(v, n) => [fmtMoney(String(v), locale), n === "net" ? L("淨損益", "Net P&L") : L("未計費用損益", "P&L before costs")]} contentStyle={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12 }} />
            <ReferenceLine y={0} stroke="var(--text-3)" />
            <Line type="monotone" dataKey="gross" stroke="var(--chart-2)" dot={false} strokeWidth={2} isAnimationActive={false} />
            <Line type="monotone" dataKey="net" stroke="var(--chart-1)" dot={false} strokeWidth={2} strokeDasharray="4 3" isAnimationActive={false} />
            <ReferenceLine x={cur?.price} stroke="var(--blue)" strokeDasharray="2 3" />
          </LineChart>
        </ChartBlock>
        <ChartBlock title={t("debt")} small>
          <LineChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid stroke="var(--chart-grid)" vertical={false} />
            <XAxis dataKey="price" type="number" domain={["dataMin", "dataMax"]} tick={axis} tickFormatter={(v) => fmtNum(v, locale, 0)} />
            <YAxis tick={axis} width={58} tickFormatter={(v) => fmtNum(v / 1000, locale, 0) + "k"} />
            <Tooltip formatter={(v, n) => [fmtMoney(String(v), locale), n === "mv" ? L("市值", "Market value") : L("融資負債", "Margin loan")]} contentStyle={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12 }} />
            <Line type="monotone" dataKey="mv" stroke="var(--chart-1)" dot={false} strokeWidth={2} isAnimationActive={false} />
            <Line type="monotone" dataKey="debt" stroke="var(--risk-critical)" dot={false} strokeWidth={2} strokeDasharray="5 4" isAnimationActive={false} />
            <ReferenceLine x={cur?.price} stroke="var(--blue)" strokeDasharray="2 3" />
          </LineChart>
        </ChartBlock>
      </div>
      <details className="rounded-[8px] border border-line px-3 py-2 text-[12px]">
        <summary className="cursor-pointer text-ink-2">{t("table")}</summary>
        <div className="mt-2 max-h-56 overflow-auto">
          <table className="num w-full text-left">
            <caption className="sr-only">{t("ratio")}</caption>
            <thead><tr className="text-ink-3"><th scope="col">{L("價格", "Price")}</th><th scope="col">{L("維持率%", "Ratio %")}</th><th scope="col">{L("未計費用損益", "P&L before costs")}</th><th scope="col">{L("市值", "Market value")}</th><th scope="col">{L("融資", "Loan")}</th></tr></thead>
            <tbody>
              {data.filter((_, i) => i % 3 === 0).map((d) => (
                <tr key={d.price} className="border-t border-line"><td>{d.price}</td><td>{d.ratio ?? "—"}</td><td>{d.gross}</td><td>{d.mv}</td><td>{d.debt}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </div>
  );
}

function ChartBlock({ title, summary, children, small }: { title: string; summary?: string; children: React.ReactElement; small?: boolean }) {
  return (
    <figure>
      <figcaption className="mb-1 flex items-baseline justify-between text-[13px] font-semibold text-ink-2">
        <span>{title}</span>
        {summary ? <span className="text-[12px] font-normal text-ink-3">{summary}</span> : null}
      </figcaption>
      <div className={small ? "h-44" : "h-60"} role="img" aria-label={`${title}${summary ? `，${summary}` : ""}`}>
        <ResponsiveContainer width="100%" height="100%">{children}</ResponsiveContainer>
      </div>
    </figure>
  );
}
