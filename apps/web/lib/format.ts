import { useSyncExternalStore } from "react";
import Decimal from "decimal.js";

export function cn(...c: (string | false | null | undefined)[]) {
  return c.filter(Boolean).join(" ");
}

export function fmtNum(v: string | number | null | undefined, locale = "zh-TW", digits?: number): string {
  if (v === null || v === undefined || v === "" || v === "None") return "—";
  const d = new Decimal(String(v));
  const opts: Intl.NumberFormatOptions =
    digits !== undefined ? { minimumFractionDigits: digits, maximumFractionDigits: digits } : { maximumFractionDigits: 2 };
  return new Intl.NumberFormat(locale, opts).format(d.toNumber());
}

export function fmtMoney(v: string | number | null | undefined, locale = "zh-TW") {
  if (v === null || v === undefined || v === "" || v === "None") return "—";
  return new Intl.NumberFormat(locale, { style: "currency", currency: "TWD", maximumFractionDigits: 0 }).format(
    new Decimal(String(v)).toNumber(),
  );
}

export function fmtValue(v: string | null | undefined, unit: string, locale = "zh-TW") {
  if (v === null || v === undefined || v === "None") return "—";
  if (unit === "TWD") return fmtMoney(v, locale);
  if (unit === "percent") return `${fmtNum(v, locale, 2)}%`;
  if (unit === "price") return fmtNum(v, locale, 2);
  if (unit === "shares") return `${fmtNum(v, locale, 0)}`;
  return fmtNum(v, locale);
}

export function fmtDate(v: string | null | undefined, locale = "zh-TW", withTime = false) {
  if (!v) return "—";
  const d = new Date(v.length <= 10 ? `${v}T00:00:00+08:00` : v);
  return new Intl.DateTimeFormat(locale, {
    timeZone: "Asia/Taipei",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    ...(withTime ? { hour: "2-digit", minute: "2-digit" } : {}),
  }).format(d);
}

export function todayTW(): string {
  const parts = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Taipei" }).format(new Date());
  return parts;
}

export function nextWeekday(iso = todayTW()): string {
  const d = new Date(`${iso}T00:00:00Z`);
  while (d.getUTCDay() === 0 || d.getUTCDay() === 6) d.setUTCDate(d.getUTCDate() + 1);
  return d.toISOString().slice(0, 10);
}

/** 只在瀏覽器端取得今天日期（Asia/Taipei）；預先渲染時回傳空字串。 */
const noopSubscribe = () => () => {};

export function useToday(): string {
  return useSyncExternalStore(noopSubscribe, todayTW, () => "");
}

/** 是否已在瀏覽器端掛載（伺服器渲染時為 false）。 */
export function useMounted(): boolean {
  return useSyncExternalStore(noopSubscribe, () => true, () => false);
}
