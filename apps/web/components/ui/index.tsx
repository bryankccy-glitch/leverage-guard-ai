"use client";

import { AlertTriangle, CheckCircle2, CircleDashed, CircleHelp, Info, Lock, ShieldAlert, XCircle } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode, SelectHTMLAttributes } from "react";
import { forwardRef, useId } from "react";
import { useIsEn } from "@/lib/i18n";
import { ApiError } from "@/lib/api";
import { cn } from "@/lib/format";

type BtnVariant = "primary" | "secondary" | "ghost" | "danger" | "pill" | "inverse";
const BTN: Record<BtnVariant, string> = {
  primary: "bg-brand text-brand-fg hover:opacity-90",
  secondary: "border border-line bg-surface text-ink hover:bg-surface-muted",
  ghost: "text-ink-2 hover:bg-surface-muted hover:text-ink",
  danger: "bg-critical text-white hover:opacity-90",
  pill: "rounded-full border border-line bg-surface text-ink hover:bg-surface-muted",
  inverse: "rounded-full bg-ink text-bg hover:opacity-90",
};

export const Button = forwardRef<HTMLButtonElement, ButtonHTMLAttributes<HTMLButtonElement> & { variant?: BtnVariant; size?: "sm" | "md" | "lg" }>(
  function Button({ variant = "primary", size = "md", className, ...p }, ref) {
    return (
      <button
        ref={ref}
        className={cn(
          "inline-flex items-center justify-center gap-2 rounded-[8px] font-medium transition-[background,opacity,color] duration-150 disabled:cursor-not-allowed disabled:opacity-50",
          size === "sm" ? "h-8 px-3 text-[13px]" : size === "lg" ? "h-12 px-6 text-[15px]" : "h-10 px-4 text-[14px]",
          BTN[variant],
          className,
        )}
        {...p}
      />
    );
  },
);

export function LinkButton({ href, children, variant = "primary", className, size = "md" }: { href: string; children: ReactNode; variant?: BtnVariant; className?: string; size?: "sm" | "md" | "lg" }) {
  return (
    <Link
      href={href}
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-[8px] font-medium transition-[background,opacity] duration-150",
        size === "sm" ? "h-8 px-3 text-[13px]" : size === "lg" ? "h-12 px-6 text-[15px]" : "h-10 px-4 text-[14px]",
        BTN[variant],
        className,
      )}
    >
      {children}
    </Link>
  );
}

export function Card({ children, className, as: As = "section", ...rest }: { children: ReactNode; className?: string; as?: "section" | "div" | "article"; "aria-labelledby"?: string }) {
  return (
    <As className={cn("rounded-[12px] border border-line bg-surface shadow-card", className)} {...rest}>
      {children}
    </As>
  );
}

export function CardHeader({ title, desc, action, id }: { title: ReactNode; desc?: ReactNode; action?: ReactNode; id?: string }) {
  return (
    <div className="flex items-start justify-between gap-3 px-5 pt-5">
      <div className="min-w-0">
        <h2 id={id} className="text-[17px] font-semibold text-ink">{title}</h2>
        {desc ? <p className="mt-0.5 text-[13px] text-ink-3">{desc}</p> : null}
      </div>
      {action}
    </div>
  );
}

export function PageHeader({ title, subtitle, actions, badge }: { title: ReactNode; subtitle?: ReactNode; actions?: ReactNode; badge?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
      <div>
        <div className="flex flex-wrap items-center gap-2">
          <h1 className="text-[26px] font-bold leading-tight tracking-tight text-ink md:text-[30px]">{title}</h1>
          {badge}
        </div>
        {subtitle ? <p className="mt-1 max-w-3xl text-[14px] text-ink-2">{subtitle}</p> : null}
      </div>
      {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
    </div>
  );
}

type Tone = "brand" | "blue" | "critical" | "high" | "warning" | "normal" | "unknown";
// 標籤與提示框文字使用 *-ink（淺色模式較深），12px 文字對比 ≥ 4.5:1
const TONE: Record<Tone, string> = {
  brand: "bg-brand-soft text-brand-ink",
  blue: "bg-blue-soft text-blue-ink",
  critical: "bg-critical-soft text-critical-ink",
  high: "bg-high-soft text-high-ink",
  warning: "bg-warning-soft text-warning-ink",
  normal: "bg-normal-soft text-normal-ink",
  unknown: "bg-unknown-soft text-unknown-ink",
};

export function Badge({ tone = "unknown", children, className, icon }: { tone?: Tone; children: ReactNode; className?: string; icon?: ReactNode }) {
  return (
    <span className={cn("inline-flex items-center gap-1 whitespace-nowrap rounded-full px-2.5 py-0.5 text-[12px] font-medium", TONE[tone], className)}>
      {icon}
      {children}
    </span>
  );
}

/** 法律事件狀態：顏色＋圖示＋文字，不只用顏色表示。 */
export function EventStatus({ status }: { status: string }) {
  const t = useTranslations("timeline.status");
  const map: Record<string, [Tone, ReactNode]> = {
    triggered_in_simulation: ["critical", <ShieldAlert key="i" size={13} aria-hidden />],
    requires_confirmation: ["warning", <CircleHelp key="i" size={13} aria-hidden />],
    potential: ["high", <AlertTriangle key="i" size={13} aria-hidden />],
    resolved: ["normal", <CheckCircle2 key="i" size={13} aria-hidden />],
    not_triggered: ["unknown", <CircleDashed key="i" size={13} aria-hidden />],
  };
  const [tone, icon] = map[status] ?? ["unknown", <CircleDashed key="i" size={13} aria-hidden />];
  return (
    <Badge tone={tone} icon={icon}>
      {t.has(status) ? t(status) : status}
    </Badge>
  );
}

/** tip：說明收成標籤旁的 ⓘ（滑鼠移上去顯示；螢幕閱讀器照常讀到），讓密集的表單比較清爽。 */
export function Field({ label, hint, error, children, htmlFor, tip }: { label: ReactNode; hint?: ReactNode; error?: string; children: ReactNode; htmlFor?: string; tip?: boolean }) {
  const tipText = tip && typeof hint === "string" ? hint : null;
  return (
    <div className="space-y-1">
      <label htmlFor={htmlFor} className="flex items-center gap-1 text-[13px] font-medium text-ink-2">
        {label}
        {tipText ? (
          <span title={tipText} className="inline-flex cursor-help text-ink-3">
            <Info size={13} aria-hidden />
            <span className="sr-only">（{tipText}）</span>
          </span>
        ) : null}
      </label>
      {children}
      {error ? (
        <p role="alert" className="flex items-center gap-1 text-[12px] text-critical">
          <XCircle size={12} aria-hidden /> {error}
        </p>
      ) : hint && !tipText ? (
        <p className="text-[12px] text-ink-3">{hint}</p>
      ) : null}
    </div>
  );
}

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement> & { invalid?: boolean }>(function Input({ className, invalid, ...p }, ref) {
  return (
    <input
      ref={ref}
      aria-invalid={invalid || undefined}
      className={cn(
        "num h-10 w-full rounded-[8px] border bg-surface px-3 text-[14px] text-ink placeholder:text-ink-3",
        invalid ? "border-critical" : "border-line",
        className,
      )}
      {...p}
    />
  );
});

export function Select({ className, children, ...p }: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select className={cn("h-10 rounded-[8px] border border-line bg-surface px-3 text-[14px] text-ink", className ?? "w-full")} {...p}>
      {children}
    </select>
  );
}

export function NumberField({ label, value, onChange, suffix, error, hint, step = "any", min, tip }: { label: ReactNode; value: string; onChange: (v: string) => void; suffix?: string; error?: string; hint?: ReactNode; step?: string; min?: string; tip?: boolean }) {
  const id = useId();
  return (
    <Field label={label} htmlFor={id} error={error} hint={hint} tip={tip}>
      <div className="relative">
        <Input id={id} inputMode="decimal" type="number" step={step} min={min} value={value} invalid={!!error} onChange={(e) => onChange(e.target.value)} className={suffix ? "pr-12" : ""} />
        {suffix ? <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-[12px] text-ink-3">{suffix}</span> : null}
      </div>
    </Field>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("skeleton rounded-[8px]", className)} aria-hidden />;
}

export function LoadingBlock({ rows = 3 }: { rows?: number }) {
  const t = useTranslations("common");
  return (
    <div role="status" aria-live="polite" className="space-y-2 p-5">
      <span className="sr-only">{t("loading")}</span>
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} className="h-5 w-full" />
      ))}
    </div>
  );
}

export function EmptyState({ title, desc, action, icon }: { title: ReactNode; desc?: ReactNode; action?: ReactNode; icon?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 px-6 py-10 text-center">
      <div className="text-ink-3">{icon ?? <Info size={28} aria-hidden />}</div>
      <p className="font-medium text-ink">{title}</p>
      {desc ? <p className="max-w-md text-[13px] text-ink-3">{desc}</p> : null}
      {action}
    </div>
  );
}

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const isEn = useIsEn();
  const t = useTranslations("common");
  const e = error instanceof ApiError ? error : null;
  if (e?.status === 401) return <UnauthorizedState />;
  return (
    <div role="alert" className="m-5 flex flex-col gap-2 rounded-[12px] border border-critical/30 bg-critical-soft p-4">
      <p className="flex items-center gap-2 font-medium text-critical">
        <XCircle size={16} aria-hidden /> {e?.status === 403 ? t("forbidden") : t("error")}
      </p>
      <p className="text-[13px] text-ink-2">{e?.message ?? String(error)}</p>
      {e?.requestId ? <p className="num text-[12px] text-ink-3">{t("requestId")}{isEn ? ": " : "："}{e.requestId}</p> : null}
      {onRetry ? (
        <div>
          <Button variant="secondary" size="sm" onClick={onRetry}>{t("retry")}</Button>
        </div>
      ) : null}
    </div>
  );
}

export function UnauthorizedState() {
  const t = useTranslations();
  return (
    <EmptyState
      icon={<Lock size={28} aria-hidden />}
      title={t("common.unauthorized")}
      desc={t("dashboard.loginPrompt")}
      action={<LinkButton href="/login" size="sm">{t("shell.login")}</LinkButton>}
    />
  );
}

export function SuccessNote({ children }: { children: ReactNode }) {
  return (
    <p role="status" className="flex items-center gap-2 rounded-[8px] bg-normal-soft px-3 py-2 text-[13px] text-normal">
      <CheckCircle2 size={14} aria-hidden /> {children}
    </p>
  );
}

export function Notice({ tone = "blue", children, title }: { tone?: Tone; children: ReactNode; title?: ReactNode }) {
  return (
    <div className={cn("rounded-[12px] px-4 py-3 text-[13px]", TONE[tone])}>
      {title ? <p className="mb-0.5 font-semibold">{title}</p> : null}
      <div className="text-ink-2">{children}</div>
    </div>
  );
}

export function SimBadge() {
  const t = useTranslations("common");
  return <Badge tone="blue">{t("simulationData")}</Badge>;
}

export function NotAvailable({ phase }: { phase: string }) {
  const t = useTranslations("common");
  return (
    <Card>
      <EmptyState icon={<CircleDashed size={28} aria-hidden />} title={t("notAvailable")} desc={t("notAvailableDesc", { phase })} />
    </Card>
  );
}
