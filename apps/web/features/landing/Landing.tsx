"use client";

import * as Slider from "@radix-ui/react-slider";
import { motion } from "motion/react";
import { ArrowRight, Bot, Calculator, CheckCircle2, FileSearch, Gavel, Layers3, Scale, ShieldCheck, Timer, UserRound } from "lucide-react";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { useState, type ReactNode } from "react";
import { LinkButton } from "@/components/ui";
import { cn, fmtMoney, fmtNum } from "@/lib/format";
import { marginPreview } from "@/lib/margin-preview";
import { PublicFooter, PublicNav } from "./PublicChrome";

export function Landing() {
  const t = useTranslations("landing");
  return (
    <div className="min-h-screen bg-bg">
      <PublicNav />
      <main id="main">
        <section className="mx-auto grid max-w-7xl gap-10 px-5 pb-16 pt-10 lg:grid-cols-[1.05fr_1fr] lg:pt-16">
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }} className="flex flex-col justify-center">
            <p className="mb-4 inline-flex w-fit items-center gap-2 rounded-full border border-line bg-surface px-3 py-1 text-[12px] text-ink-2">
              <ShieldCheck size={14} className="text-brand" aria-hidden /> Know the Risk. Understand Your Rights.
            </p>
            <h1 className="text-balance text-[34px] font-bold leading-[1.2] tracking-tight text-ink md:text-[44px]">
              {t("heroTitle1")}
              <br />
              <span className="text-brand">{t("heroTitle2")}</span>
            </h1>
            <p className="mt-3 text-[17px] font-medium text-ink-2">{t("heroSubEn")}</p>
            <p className="mt-4 max-w-xl text-[16px] text-ink-2">{t("heroDesc")}</p>
            <div className="mt-7 flex flex-wrap gap-3">
              <LinkButton href="/simulator/margin" size="lg">{t("ctaPrimary")} <ArrowRight size={16} /></LinkButton>
              <LinkButton href="/legal/rights" size="lg" variant="secondary">{t("ctaSecondary")}</LinkButton>
            </div>
            <p className="mt-4 text-[13px] text-ink-3">{t("noLogin")}</p>
          </motion.div>
          <HeroPreview />
        </section>

        <section id="risk" className="border-y border-line bg-surface">
          <div className="mx-auto max-w-7xl px-5 py-16">
            <h2 className="text-[30px] font-bold tracking-tight text-ink">{t("hiddenTitle")}</h2>
            <p className="mt-2 text-ink-2">{t("hiddenDesc")}</p>
            <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {(["principal", "call", "disposal", "debt", "unmatched", "settlement"] as const).map((k, i) => {
                const [title, desc] = t.raw(`hidden.${k}`) as [string, string];
                return (
                  <div key={k} className="rounded-[12px] border border-line bg-bg p-5">
                    <p className="num text-[13px] font-semibold text-brand">0{i + 1}</p>
                    <p className="mt-1 text-[17px] font-semibold text-ink">{title}</p>
                    <p className="mt-1.5 text-[14px] text-ink-2">{desc}</p>
                  </div>
                );
              })}
            </div>
          </div>
        </section>

        <section id="features" className="mx-auto max-w-7xl px-5 py-16">
          <h2 className="text-[30px] font-bold tracking-tight text-ink">{t("featuresTitle")}</h2>
          <div className="mt-8 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {([
              ["twin", <UserRound key="i" size={20} />, "/digital-twin"],
              ["risk", <Calculator key="i" size={20} />, "/simulator/margin"],
              ["timeline", <Timer key="i" size={20} />, "/legal/timeline"],
              ["contract", <FileSearch key="i" size={20} />, "/contracts"],
              ["rac", <Layers3 key="i" size={20} />, "/admin/legal-rules"],
              ["agents", <Bot key="i" size={20} />, "/agents"],
            ] as const).map(([k, icon, href]) => {
              const [title, desc] = t.raw(`features.${k}`) as [string, string];
              return (
                <Link key={k} href={href} className="group rounded-[12px] border border-line bg-surface p-6 shadow-card transition-colors hover:border-brand">
                  <span className="grid h-11 w-11 place-items-center rounded-[10px] bg-brand-soft text-brand">{icon}</span>
                  <p className="mt-4 text-[17px] font-semibold text-ink">{title}</p>
                  <p className="mt-1.5 text-[14px] text-ink-2">{desc}</p>
                  <ArrowRight size={16} className="mt-3 text-ink-3 transition-transform group-hover:translate-x-1 group-hover:text-brand" aria-hidden />
                </Link>
              );
            })}
          </div>
        </section>

        <section id="how" className="bg-navy text-white dark:bg-surface">
          <div className="mx-auto max-w-7xl px-5 py-16">
            <h2 className="text-[30px] font-bold tracking-tight">{t("howTitle")}</h2>
            <ol className="mt-8 grid gap-4 md:grid-cols-5">
              {(t.raw("how") as string[]).map((step, i) => (
                <li key={step} className="relative rounded-[12px] border border-white/15 p-5">
                  <span className="num text-[13px] text-[#2DD4BF]">STEP {i + 1}</span>
                  <p className="mt-1 text-[18px] font-semibold">{step}</p>
                  <p className="mt-1 text-[13px] text-white/70">{(t.raw("howDesc") as string[])[i]}</p>
                </li>
              ))}
            </ol>
          </div>
        </section>

        <section id="trust" className="mx-auto max-w-7xl px-5 py-16">
          <h2 className="text-[30px] font-bold tracking-tight text-ink">{t("trustTitle")}</h2>
          <ul className="mt-6 grid gap-3 md:grid-cols-2">
            {(t.raw("trust") as string[]).map((x) => (
              <li key={x} className="flex items-start gap-3 rounded-[12px] border border-line bg-surface p-4 text-[15px] text-ink">
                <CheckCircle2 size={18} className="mt-0.5 shrink-0 text-normal" aria-hidden /> {x}
              </li>
            ))}
          </ul>
        </section>
      </main>
      <PublicFooter />
    </div>
  );
}

function HeroPreview() {
  const t = useTranslations("landing");
  const locale = useLocale();
  const [price, setPrice] = useState(100);
  const p = marginPreview({ buyPrice: "100", quantity: "1000", financingRatio: "0.6", currentPrice: String(price), threshold: "1.30" });
  const ratio = p?.ratioPct ? Number(p.ratioPct) : 0;
  const events = [
    { key: "open", label: "建立融資部位（自備 40,000、融資 60,000）", on: true },
    { key: "breach", label: "維持率低於 130%：符合補繳通知條件", on: ratio < 130 },
    { key: "deadline", label: "通知送達後 2 個營業日內補繳差額", on: ratio < 130 },
    { key: "debt", label: "市值低於借款：處分後可能仍有剩餘債務", on: ratio < 100 },
  ];
  const explain =
    ratio >= 166
      ? "股價還在買進價附近，維持率約 166%。這不代表安全：融資讓每 1 元的跌幅，對本金的影響放大約 2.5 倍。"
      : ratio >= 130
        ? `本金已虧損 ${fmtMoney(String(-Number(p?.grossPnl ?? 0)), locale)}，但維持率仍高於 130%，還沒有符合追繳條件。`
        : ratio >= 100
          ? `維持率 ${p?.ratioPct}% 已低於 130%：券商應通知你補繳差額，估計約 ${fmtMoney(p?.callAmount, locale)}（依第 54 條公式）。`
          : `市值已低於融資借款。即使擔保品全部賣出，也不足以清償，差額仍需補足——本金虧完不代表債務結束。`;
  return (
    <motion.div initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.35, delay: 0.05 }} id="preview" className="rounded-[16px] border border-line bg-surface p-5 shadow-card">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-[15px] font-semibold text-ink">{t("previewTitle")}</p>
          <p className="text-[12px] text-ink-3">{t("previewDesc")}</p>
        </div>
        <span className="rounded-full bg-blue-soft px-2.5 py-0.5 text-[11px] font-medium text-blue">Simulation</span>
      </div>
      <div className="mt-4 grid grid-cols-3 gap-2">
        <Stat label="擔保維持率" value={`${p?.ratioPct ?? "—"}%`} tone={ratio < 130 ? "critical" : undefined} />
        <Stat label="未計費用損益" value={fmtMoney(p?.grossPnl, locale)} tone={Number(p?.grossPnl) < 0 ? "critical" : undefined} />
        <Stat label="帳戶淨值" value={fmtMoney(p?.equity, locale)} tone={Number(p?.equity) < 0 ? "critical" : undefined} />
      </div>
      <div className="mt-4">
        <div className="mb-1 flex items-baseline justify-between">
          <label htmlFor="hero-price" className="text-[13px] text-ink-2">{t("priceLabel")}</label>
          <span className="num text-[22px] font-bold text-ink">{fmtNum(price, locale, 2)}</span>
        </div>
        <Slider.Root id="hero-price" className="relative flex h-6 w-full touch-none select-none items-center" min={40} max={120} step={1} value={[price]} onValueChange={([v]) => setPrice(v)} aria-label={t("priceLabel")}>
          <Slider.Track className="relative h-2 grow rounded-full bg-line"><Slider.Range className="absolute h-full rounded-full bg-brand" /></Slider.Track>
          <Slider.Thumb aria-label={t("priceLabel")} className="block h-6 w-6 rounded-full border-2 border-brand bg-surface shadow" />
        </Slider.Root>
        <RatioBar ratio={ratio} />
      </div>
      <ol className="mt-4 space-y-2" aria-label="法律事件">
        {events.map((e) => (
          <li key={e.key} className={cn("flex items-center gap-2 rounded-[10px] border px-3 py-2 text-[13px] transition-colors", e.on ? (e.key === "open" ? "border-line text-ink" : "border-critical/40 bg-critical-soft text-ink") : "border-dashed border-line text-ink-3")}>
            {e.on ? <Gavel size={14} className={e.key === "open" ? "text-brand" : "text-critical"} aria-hidden /> : <Scale size={14} aria-hidden />}
            <span className="flex-1">{e.label}</span>
            <span className="text-[11px]">{e.on ? (e.key === "open" ? "已建立" : "模擬中觸發") : "未觸發"}</span>
          </li>
        ))}
      </ol>
      <p className="mt-3 rounded-[10px] bg-brand-soft px-3 py-2 text-[13px] text-ink" aria-live="polite">{explain}</p>
      <p className="mt-2 text-[11px] text-ink-3">示範以前端 Decimal.js 即時試算；完整模擬由後端引擎計算並附官方條文。</p>
    </motion.div>
  );
}

function Stat({ label, value, tone }: { label: string; value: string; tone?: "critical" }) {
  return (
    <div className="rounded-[10px] bg-surface-muted p-3">
      <p className="text-[11px] text-ink-3">{label}</p>
      <p className={cn("num mt-0.5 text-[17px] font-bold", tone === "critical" ? "text-critical" : "text-ink")}>{value}</p>
    </div>
  );
}

function RatioBar({ ratio }: { ratio: number }) {
  const pct = Math.max(0, Math.min(100, (ratio / 200) * 100));
  return (
    <div className="mt-3" aria-hidden>
      <div className="relative h-2 rounded-full bg-surface-muted">
        <div className={cn("absolute h-2 rounded-full transition-[width] duration-150", ratio < 130 ? "bg-critical" : "bg-brand")} style={{ width: `${pct}%` }} />
        <span className="absolute -top-1 h-4 w-0.5 bg-critical" style={{ left: "65%" }} />
        <span className="absolute -top-1 h-4 w-0.5 bg-normal" style={{ left: "83%" }} />
      </div>
      <div className="relative mt-1 h-4 text-[10px] text-ink-3">
        <span className="absolute -translate-x-1/2" style={{ left: "65%" }}>130%</span>
        <span className="absolute -translate-x-1/2" style={{ left: "83%" }}>166%</span>
      </div>
    </div>
  );
}

export function Section({ children }: { children: ReactNode }) {
  return <section className="mx-auto max-w-4xl px-5 py-12">{children}</section>;
}
