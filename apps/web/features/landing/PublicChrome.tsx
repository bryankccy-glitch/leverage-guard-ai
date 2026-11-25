"use client";

import { Languages, Menu, Moon, Sun, X } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { useTheme } from "next-themes";
import { useState } from "react";
import { useMounted } from "@/lib/format";
import { LogoHorizontal } from "@/components/brand/Logo";
import { useUI } from "@/stores/auth";

export function PublicNav() {
  const t = useTranslations();
  const [open, setOpen] = useState(false);
  const { resolvedTheme, setTheme } = useTheme();
  const locale = useUI((s) => s.locale);
  const setLocale = useUI((s) => s.setLocale);
  const mounted = useMounted();
  const links = [
    ["/simulator/margin", t("landing.navRisk")],
    ["/legal/rights", t("landing.navRights")],
    ["/contracts", t("landing.navContracts")],
    ["/how-it-works", t("landing.navHow")],
  ];
  return (
    <header className="sticky top-0 z-30 border-b border-line bg-bg/85 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-7xl items-center gap-6 px-5">
        <Link href="/" aria-label="LeverageGuard AI 首頁"><LogoHorizontal /></Link>
        <nav aria-label="主要" className="hidden flex-1 items-center gap-6 text-[14px] text-ink-2 md:flex">
          {links.map(([href, label]) => <Link key={href} href={href} className="hover:text-ink">{label}</Link>)}
        </nav>
        <div className="ml-auto flex items-center gap-2">
          <button onClick={() => setLocale(locale === "en" ? "zh-TW" : "en")} aria-label={t("shell.language")} className="grid h-9 w-9 place-items-center rounded-full text-ink-2 hover:bg-surface-muted"><Languages size={17} /></button>
          <button onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")} aria-label={t("shell.theme")} className="grid h-9 w-9 place-items-center rounded-full text-ink-2 hover:bg-surface-muted">
            {mounted && resolvedTheme === "dark" ? <Sun size={17} /> : <Moon size={17} />}
          </button>
          <Link href="/login" className="hidden h-9 items-center rounded-[8px] px-3 text-[14px] text-ink hover:bg-surface-muted sm:flex">{t("shell.login")}</Link>
          <Link href="/simulator/margin" className="flex h-9 items-center rounded-[8px] bg-brand px-4 text-[14px] font-medium text-brand-fg hover:opacity-90">{t("landing.start")}</Link>
          <button onClick={() => setOpen(!open)} aria-label={t("shell.openMenu")} aria-expanded={open} className="grid h-9 w-9 place-items-center rounded-full md:hidden">{open ? <X size={18} /> : <Menu size={18} />}</button>
        </div>
      </div>
      {open ? (
        <nav className="space-y-1 border-t border-line px-5 py-3 md:hidden">
          {links.map(([href, label]) => <Link key={href} href={href} className="block rounded-[8px] px-2 py-2 text-ink hover:bg-surface-muted">{label}</Link>)}
          <Link href="/login" className="block rounded-[8px] px-2 py-2 text-ink hover:bg-surface-muted">{t("shell.login")}</Link>
        </nav>
      ) : null}
    </header>
  );
}

export function PublicFooter() {
  const t = useTranslations();
  return (
    <footer className="border-t border-line bg-surface">
      <div className="mx-auto grid max-w-7xl gap-8 px-5 py-12 md:grid-cols-4">
        <div className="space-y-3 md:col-span-1">
          <LogoHorizontal />
          <p className="text-[13px] text-ink-3">{t("common.slogan")}</p>
          <p className="text-[12px] text-ink-3">{t("common.notAdvice")}</p>
        </div>
        <div>
          <p className="mb-2 text-[13px] font-semibold text-ink">產品</p>
          <ul className="space-y-1.5 text-[13px] text-ink-2">
            <li><Link href="/about" className="hover:text-ink">關於</Link></li>
            <li><Link href="/how-it-works" className="hover:text-ink">{t("landing.navHow")}</Link></li>
            <li><Link href="/simulator/margin" className="hover:text-ink">{t("nav.margin")}</Link></li>
            <li><Link href="/simulator/day-trading" className="hover:text-ink">{t("nav.dayTrading")}</Link></li>
          </ul>
        </div>
        <div>
          <p className="mb-2 text-[13px] font-semibold text-ink">{t("landing.footerSources")}</p>
          <ul className="space-y-1.5 text-[13px] text-ink-2">
            <li><a href="https://law.moj.gov.tw/" target="_blank" rel="noopener noreferrer" className="hover:text-ink">全國法規資料庫</a></li>
            <li><a href="https://twse-regulation.twse.com.tw/" target="_blank" rel="noopener noreferrer" className="hover:text-ink">臺灣證券交易所法規分享知識庫</a></li>
            <li><a href="https://www.foi.org.tw/" target="_blank" rel="noopener noreferrer" className="hover:text-ink">金融消費評議中心</a></li>
            <li><Link href="/legal-resources" className="hover:text-ink">所有資料來源</Link></li>
          </ul>
        </div>
        <div>
          <p className="mb-2 text-[13px] font-semibold text-ink">條款與隱私</p>
          <ul className="space-y-1.5 text-[13px] text-ink-2">
            <li><Link href="/privacy" className="hover:text-ink">隱私政策</Link></li>
            <li><Link href="/terms" className="hover:text-ink">使用條款</Link></li>
            <li><span>聯絡：本專案展示用信箱尚未設定</span></li>
          </ul>
          <p className="mt-3 text-[12px] text-ink-3">{t("landing.footerLimits")}</p>
        </div>
      </div>
    </footer>
  );
}
