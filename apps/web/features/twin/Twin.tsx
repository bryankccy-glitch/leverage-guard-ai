"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2 } from "lucide-react";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";
import { demoSwap, useIsEn, useL } from "@/lib/i18n";
import { Badge, Button, Card, CardHeader, EmptyState, ErrorState, Field, Input, LoadingBlock, Notice, NumberField, Select, SimBadge } from "@/components/ui";
import { api } from "@/lib/api";
import { cn, fmtMoney, fmtNum } from "@/lib/format";
import { useAuth } from "@/stores/auth";

type Position = { id: string; asset_label: string; trading_type: string; quantity: string; entry_price: string; simulated_price: string; financing_principal: string; financing_ratio: string | null; interest_rate: string | null; trading_date: string };
type Account = { id: string; name: string; account_type: string; cash_balance: string; positions: Position[]; financial_state: { market_value: string; borrowed: string; own_equity: string; unrealized_pnl: string; account_ratio: null | Record<string, { value: string | null }> } };

export function DigitalTwin() {
  const t = useTranslations("twin");
  const L = useL();
  const locale = useLocale();
  const token = useAuth((s) => s.token);
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["accounts", token], queryFn: () => api<{ items: Account[] }>("/accounts"), enabled: !!token });
  const refresh = () => qc.invalidateQueries({ queryKey: ["accounts"] });
  const [nameState, setName] = useState("我的模擬融資帳戶");
  const isEn = useIsEn();
  const name = demoSwap(nameState, isEn);
  const [type, setType] = useState("margin");
  const create = useMutation({ mutationFn: () => api("/accounts", { body: { name, account_type: type, cash_balance: "0" } }), onSuccess: refresh });
  if (!token) return <Card><EmptyState title={L("登入後可以建立虛擬帳戶", "Log in to create a virtual account")} /></Card>;
  if (q.isLoading) return <Card><LoadingBlock rows={6} /></Card>;
  if (q.error) return <Card><ErrorState error={q.error} /></Card>;
  return (
    <div className="space-y-5">
      <Notice tone="blue">{t("subtitle")}</Notice>
      {q.data!.items.map((a) => <AccountCard key={a.id} a={a} onChange={refresh} locale={locale} />)}
      <Card>
        <CardHeader title={t("newAccount")} />
        <div className="grid gap-3 p-5 md:grid-cols-[1fr_200px_auto] md:items-end">
          <Field label={t("accountName")} htmlFor="acc-name"><Input id="acc-name" value={name} onChange={(e) => setName(e.target.value)} maxLength={80} /></Field>
          <Field label={t("accountType")} htmlFor="acc-type">
            <Select id="acc-type" value={type} onChange={(e) => setType(e.target.value)}>
              {(["cash", "margin", "day_trading", "portfolio"] as const).map((k) => <option key={k} value={k}>{t(`types.${k}`)}</option>)}
            </Select>
          </Field>
          <Button onClick={() => create.mutate()} disabled={create.isPending}><Plus size={15} />{t("newAccount")}</Button>
        </div>
        {create.error ? <ErrorState error={create.error} /> : null}
      </Card>
    </div>
  );
}

function AccountCard({ a, onChange, locale }: { a: Account; onChange: () => void; locale: string }) {
  const t = useTranslations("twin");
  const tm = useTranslations("dashboard");
  const L = useL();
  const ratio = a.financial_state.account_ratio?.account_maintenance_ratio?.value;
  const [npState, setNp] = useState({ asset_label: "示範股票（虛構）", quantity: "1000", entry_price: "50", simulated_price: "50", financing_ratio: "0.6", interest_rate: "0.0645" });
  const isEn = useIsEn();
  const np = { ...npState, asset_label: demoSwap(npState.asset_label, isEn) };
  const add = useMutation({ mutationFn: () => api(`/accounts/${a.id}/positions`, { body: { ...np, trading_type: a.account_type === "cash" ? "cash" : "margin" } }), onSuccess: onChange });
  const patch = useMutation({ mutationFn: ({ id, price }: { id: string; price: string }) => api(`/positions/${id}`, { method: "PATCH", body: { simulated_price: price } }), onSuccess: onChange });
  const del = useMutation({ mutationFn: (id: string) => api(`/positions/${id}`, { method: "DELETE" }), onSuccess: onChange });
  const below = ratio !== null && ratio !== undefined && Number(ratio) < 130;
  return (
    <Card>
      <CardHeader title={a.name} desc={t(`types.${a.account_type}`)} action={<SimBadge />} />
      <div className="grid gap-3 p-5 sm:grid-cols-2 lg:grid-cols-5">
        <Stat label={tm("accountValue")} value={fmtMoney(a.financial_state.market_value, locale)} />
        <Stat label={tm("accountBorrowed")} value={fmtMoney(a.financial_state.borrowed, locale)} />
        <Stat label={tm("accountEquity")} value={fmtMoney(a.financial_state.own_equity, locale)} />
        <Stat label={tm("accountPnl")} value={fmtMoney(a.financial_state.unrealized_pnl, locale)} danger={a.financial_state.unrealized_pnl.startsWith("-")} />
        <Stat label={tm("accountRatio")} value={ratio ? `${fmtNum(ratio, locale, 2)}%` : "—"} danger={below} />
      </div>
      <div className="grid gap-3 px-5 md:grid-cols-4">
        {(["financial", "legal", "contract", "timeline"] as const).map((k) => (
          <div key={k} className="rounded-[10px] border border-line p-3 text-[13px]">
            <p className="font-semibold text-ink">{t(`states.${k}`)}</p>
            <p className="mt-1 text-ink-2">
              {k === "financial" ? L(`${a.positions.length} 個部位`, `${a.positions.length} position(s)`) : k === "legal" ? (below ? L("整戶維持率低於 130%：模擬中符合補繳通知條件", "Account ratio below 130%: meets margin call notice conditions in the simulation") : L("目前未觸發法律事件", "No legal events triggered")) : k === "contract" ? t("noContract") : <Link className="text-blue underline" href="/scenarios/new">{L("在實驗室推演時間軸", "Play out the timeline in the lab")}</Link>}
            </p>
          </div>
        ))}
      </div>
      <div className="overflow-x-auto p-5">
        <table className="w-full min-w-[720px] text-[13px]">
          <thead><tr className="border-b border-line text-left text-ink-3"><th className="py-2">{t("positions")}</th><th className="text-right">{L("股數", "Shares")}</th><th className="text-right">{t("entry")}</th><th className="text-right">{t("simPrice")}</th><th className="text-right">{t("principal")}</th><th className="text-right">{L("未實現損益", "Unrealised P&L")}</th><th /></tr></thead>
          <tbody>
            {a.positions.map((p) => {
              const pnl = (Number(p.simulated_price) - Number(p.entry_price)) * Number(p.quantity);
              return (
                <tr key={p.id} className="border-b border-line">
                  <td className="py-2 font-medium text-ink">{p.asset_label} <Badge tone="unknown">{p.trading_type}</Badge></td>
                  <td className="num text-right">{fmtNum(p.quantity, locale, 0)}</td>
                  <td className="num text-right">{fmtNum(p.entry_price, locale, 2)}</td>
                  <td className="text-right"><input aria-label={`${p.asset_label} ${t("simPrice")}`} defaultValue={Number(p.simulated_price)} type="number" step="0.5" className="num h-8 w-24 rounded-[6px] border border-line bg-surface px-2 text-right" onBlur={(e) => e.target.value && e.target.value !== String(Number(p.simulated_price)) && patch.mutate({ id: p.id, price: e.target.value })} /></td>
                  <td className="num text-right">{fmtMoney(p.financing_principal, locale)}</td>
                  <td className={cn("num text-right", pnl < 0 ? "text-critical" : "text-ink")}>{fmtMoney(String(pnl), locale)}</td>
                  <td className="text-right"><button aria-label={L("刪除部位", "Delete position")} onClick={() => del.mutate(p.id)} className="rounded p-1 text-ink-3 hover:text-critical"><Trash2 size={14} /></button></td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {patch.error || del.error || add.error ? <ErrorState error={patch.error ?? del.error ?? add.error} /> : null}
        <div className="mt-4 grid gap-2 rounded-[12px] bg-surface-muted p-3 md:grid-cols-[1.4fr_1fr_1fr_1fr_1fr_auto] md:items-end">
          <Field label={L("名稱", "Name")} htmlFor={`np-${a.id}`}><Input id={`np-${a.id}`} value={np.asset_label} onChange={(e) => setNp({ ...np, asset_label: e.target.value })} /></Field>
          <NumberField label={L("股數", "Shares")} value={np.quantity} onChange={(v) => setNp({ ...np, quantity: v })} step="1" />
          <NumberField label={t("entry")} value={np.entry_price} onChange={(v) => setNp({ ...np, entry_price: v })} />
          <NumberField label={t("simPrice")} value={np.simulated_price} onChange={(v) => setNp({ ...np, simulated_price: v })} />
          <NumberField label={L("融資比例", "Financing ratio")} value={np.financing_ratio} onChange={(v) => setNp({ ...np, financing_ratio: v })} />
          <Button onClick={() => add.mutate()} disabled={add.isPending}><Plus size={14} />{t("newPosition")}</Button>
        </div>
      </div>
    </Card>
  );
}

function Stat({ label, value, danger }: { label: string; value: string; danger?: boolean }) {
  return (
    <div className={cn("rounded-[10px] p-3", danger ? "bg-critical-soft" : "bg-surface-muted")}>
      <p className="text-[12px] text-ink-3">{label}</p>
      <p className={cn("num text-[18px] font-bold", danger ? "text-critical" : "text-ink")}>{value}</p>
    </div>
  );
}
