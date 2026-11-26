"use client";

import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import { useQuery } from "@tanstack/react-query";
import {
  Activity, Bell, BookOpenText, ChevronDown, ChevronRight, FileSearch, FileText, FlaskConical, History, Languages,
  LayoutGrid, LifeBuoy, LogIn, LogOut, Menu, Moon, PanelLeftClose, PanelLeftOpen, Radar, Scale, Search, Settings, ShieldCheck,
  Sun, Timer, TrendingDown, Users, X, Zap,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useTheme } from "next-themes";
import { useState, type ReactNode } from "react";
import { useL, demoSwap } from "@/lib/i18n";
import { LogoHorizontal, LogoMark } from "@/components/brand/Logo";
import { api } from "@/lib/api";
import { cn, useMounted } from "@/lib/format";
import { useAuth, useUI } from "@/stores/auth";
import { signOut } from "@/lib/supabase";

type NavItem = { href: string; key: string; icon: ReactNode; badge?: number | null };

function useCounts() {
  const token = useAuth((s) => s.token);
  return useQuery({
    queryKey: ["shell-counts", token],
    enabled: !!token,
    queryFn: () => api<{ kpis: Record<string, number> }>("/dashboard"),
    refetchInterval: 60_000,
  });
}

function useHealth() {
  return useQuery({
    queryKey: ["health"],
    queryFn: () => api<{ status: string }>("/health", { auth: false }),
    refetchInterval: 30_000,
    retry: 0,
  });
}

export function useRuleVersion() {
  return useQuery({
    queryKey: ["rule-version"],
    queryFn: () =>
      api<{ rule_version: string; rules: { review_status: string }[] }>("/calculate/margin", {
        body: { buy_price: "100", quantity: "1000", financing_ratio: "0.6", current_price: "100", curve: false },
        auth: false,
      }),
    staleTime: 300_000,
  });
}

export function AppShell({ children }: { children: ReactNode }) {
  return <AppShellInner>{children}</AppShellInner>;
}

function AppShellInner({ children }: { children: ReactNode }) {
  const t = useTranslations();
  const L = useL();
  const pathname = usePathname();
  const collapsed = useUI((s) => s.sidebarCollapsed);
  const toggle = useUI((s) => s.toggleSidebar);
  const user = useAuth((s) => s.user);
  const [mobileOpen, setMobileOpen] = useState(false);
  const health = useHealth();

  // 換頁時關閉抽屜（render 期間依 pathname 調整狀態，不用 effect）
  const [lastPath, setLastPath] = useState(pathname);
  if (lastPath !== pathname) {
    setLastPath(pathname);
    setMobileOpen(false);
  }

  // 選單只留兩組主要功能；報告、紀錄、通知、設定在右上角帳號選單（減少左側長度）
  const groups: { label: string; items: NavItem[] }[] = [
    {
      label: t("nav.simulation"),
      items: [
        { href: "/dashboard", key: "nav.dashboard", icon: <LayoutGrid size={18} /> },
        { href: "/simulator/margin", key: "nav.margin", icon: <TrendingDown size={18} /> },
        { href: "/simulator/day-trading", key: "nav.dayTrading", icon: <Zap size={18} /> },
        { href: "/scenarios", key: "nav.lab", icon: <FlaskConical size={18} /> },
      ],
    },
    {
      label: t("nav.legalIntel"),
      items: [
        { href: "/legal", key: "nav.legal", icon: <BookOpenText size={18} /> },
        { href: "/legal/rights", key: "nav.rights", icon: <Scale size={18} /> },
        { href: "/legal/timeline", key: "nav.timeline", icon: <Timer size={18} /> },
        { href: "/contracts", key: "nav.contracts", icon: <FileSearch size={18} /> },
        { href: "/legal/disputes", key: "nav.disputes", icon: <LifeBuoy size={18} /> },
        { href: "/regulatory-monitor", key: "nav.regulatory", icon: <Radar size={18} /> },
      ],
    },
    ...(user && user.role !== "investor" ? [{ label: t("nav.admin"), items: [{ href: "/admin", key: "nav.admin", icon: <ShieldCheck size={18} /> }] }] : []),
  ];

  const isActive = (href: string) =>
    href === "/legal" ? pathname === "/legal" || pathname.startsWith("/legal/search") || pathname.startsWith("/legal/regulations") : pathname === href || pathname.startsWith(`${href}/`);

  const sidebar = (mobile: boolean) => (
    <nav aria-label={L("主選單", "Main menu")} className={cn("flex h-full flex-col rounded-[16px] border border-line bg-surface p-3 shadow-card", !mobile && collapsed ? "w-[68px]" : "w-[248px]")}>
      <div className={cn("mb-4 flex items-center px-1 pt-1", collapsed && !mobile ? "flex-col gap-3" : "justify-between")}>
        <Link href="/" aria-label={L("LeverageGuard AI 首頁", "LeverageGuard AI home")}>{collapsed && !mobile ? <LogoMark size={30} /> : <LogoHorizontal />}</Link>
        {mobile ? (
          <button onClick={() => setMobileOpen(false)} aria-label={t("common.close")} className="rounded-[8px] p-2 text-ink-2 hover:bg-surface-muted">
            <X size={18} />
          </button>
        ) : (
          <button onClick={toggle} aria-label={t("shell.toggleSidebar")} className="rounded-[8px] bg-surface-muted p-2 text-ink-2 hover:text-ink">
            {collapsed ? <PanelLeftOpen size={16} /> : <PanelLeftClose size={16} />}
          </button>
        )}
      </div>
      <div className="flex-1 space-y-6 overflow-y-auto pr-0.5">
        {groups.map((g) => (
          <div key={g.label}>
            {!collapsed || mobile ? <p className="mb-1 px-3 text-[11px] font-semibold uppercase tracking-wider text-ink-3">{g.label}</p> : <div className="mx-2 mb-1 border-t border-line" />}
            <ul className="space-y-0.5">
              {g.items.map((it) => {
                const active = isActive(it.href);
                return (
                  <li key={it.href}>
                    <Link
                      href={it.href}
                      aria-current={active ? "page" : undefined}
                      title={collapsed && !mobile ? t(it.key) : undefined}
                      className={cn(
                        "relative flex h-10 items-center gap-3 rounded-full px-3 text-[14px] transition-colors duration-150",
                        active ? "bg-navy font-medium text-white dark:bg-black" : "text-ink-2 hover:bg-surface-muted hover:text-ink",
                        collapsed && !mobile && "justify-center px-0",
                      )}
                    >
                      {active ? <span aria-hidden className="absolute -left-3 h-6 w-1 rounded-r-full bg-blue" /> : null}
                      <span className={cn(active ? "text-[var(--chart-2)] dark:text-brand" : "")}>{it.icon}</span>
                      {!collapsed || mobile ? <span className="flex-1 truncate">{t(it.key)}</span> : null}
                      {(!collapsed || mobile) && it.badge ? (
                        <span className={cn("num min-w-6 rounded-[6px] px-1.5 text-center text-[11px] font-semibold", active ? "bg-white/15 text-white" : "bg-surface-muted text-ink-2")}>{it.badge}</span>
                      ) : null}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </div>
      {health.isError ? (
        <div className={cn("mt-3 flex items-center gap-2 rounded-[12px] bg-critical-soft px-3 py-2.5 text-[13px] text-critical", collapsed && !mobile && "justify-center px-0")}>
          <span aria-hidden className="h-2.5 w-2.5 rounded-full bg-critical" />
          {!collapsed || mobile ? t("shell.apiOffline") : null}
        </div>
      ) : null}
    </nav>
  );

  return (
    <div className="min-h-screen bg-bg p-0 md:p-3">
      <div className="flex gap-3">
        <div className="sticky top-3 hidden h-[calc(100vh-24px)] shrink-0 md:block">{sidebar(false)}</div>
        {mobileOpen ? (
          <div className="fixed inset-0 z-40 md:hidden" role="dialog" aria-modal="true">
            <div className="absolute inset-0 bg-black/40" onClick={() => setMobileOpen(false)} />
            <div className="absolute inset-y-2 left-2">{sidebar(true)}</div>
          </div>
        ) : null}
        <div className="min-w-0 flex-1">
          <TopBar onMenu={() => setMobileOpen(true)} />
          <main id="main" className="px-4 pb-24 pt-6 md:px-4 md:pb-12">
            <Breadcrumb />
            {children}
          </main>
        </div>
      </div>
      <MobileBottomNav />
    </div>
  );
}

function TopBar({ onMenu }: { onMenu: () => void }) {
  const t = useTranslations();
  const router = useRouter();
  const { resolvedTheme, setTheme } = useTheme();
  const locale = useUI((s) => s.locale);
  const setLocale = useUI((s) => s.setLocale);
  const { user } = useAuth();
  const rv = useRuleVersion().data;
  const unread = useCounts().data?.kpis.unread ?? 0;
  const staff = !!user && user.role !== "investor"; // 規則版本是審查資訊，只給審查員與管理員看
  const [q, setQ] = useState("");
  const mounted = useMounted();
  const unreviewed = rv?.rules.filter((r) => r.review_status !== "active" && r.review_status !== "approved").length ?? 0;
  const aiChecked = !unreviewed && (rv?.rules.some((r) => r.review_status === "approved") ?? false);

  return (
    <header className="sticky top-0 z-30 bg-bg/80 backdrop-blur md:top-3 md:rounded-[16px]">
      <div className="flex items-center gap-2 border-b border-line bg-surface px-3 py-2.5 md:rounded-[16px] md:border md:px-4 md:shadow-card">
        <button onClick={onMenu} aria-label={t("shell.openMenu")} className="rounded-[8px] p-2 text-ink-2 hover:bg-surface-muted md:hidden">
          <Menu size={20} />
        </button>
        <form
          role="search"
          className="flex min-w-0 flex-1 items-center gap-2 rounded-full bg-surface-muted px-4 md:max-w-[440px]"
          onSubmit={(e) => {
            e.preventDefault();
            if (q.trim()) router.push(`/legal/search?q=${encodeURIComponent(q.trim())}`);
          }}
        >
          <Search size={17} className="shrink-0 text-ink-3" aria-hidden />
          <label htmlFor="global-search" className="sr-only">{t("common.search")}</label>
          <input id="global-search" value={q} onChange={(e) => setQ(e.target.value)} placeholder={t("shell.searchPlaceholder")} className="h-10 min-w-0 flex-1 bg-transparent text-[14px] text-ink outline-none placeholder:text-ink-3" />
        </form>
        <div className="ml-auto flex items-center gap-1.5 md:gap-2">
          {mounted && staff ? <Link href="/admin/rule-versions" className="hidden items-center gap-2 rounded-full border border-line bg-surface py-1.5 pl-1.5 pr-3 text-[13px] text-ink hover:bg-surface-muted lg:flex" title={t("common.ruleVersion")}>
            <span className="grid h-7 w-7 place-items-center rounded-full bg-ink text-bg"><Activity size={14} aria-hidden /></span>
            <span className="flex flex-col leading-tight">
              <span className="text-[11px] text-ink-3">{t("shell.ruleVersionLabel")}{mounted && unreviewed ? ` · ${t("common.unreviewed")}` : mounted && aiChecked ? ` · ${t("common.aiChecked")}` : ""}</span>
              <span className="num font-medium">{mounted ? (rv?.rule_version ?? "—") : "—"}</span>
            </span>
          </Link> : null}
          <span className="relative">
            <IconButton label={unread ? `${t("nav.notifications")} (${unread})` : t("nav.notifications")} onClick={() => router.push("/notifications")}><Bell size={18} /></IconButton>
            {mounted && unread ? <span aria-hidden className="num absolute -right-0.5 -top-0.5 grid h-[18px] min-w-[18px] place-items-center rounded-full bg-critical px-1 text-[10px] font-semibold text-white">{unread > 9 ? "9+" : unread}</span> : null}
          </span>
          <IconButton label={t("shell.theme")} onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}>
            {mounted && resolvedTheme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
          </IconButton>
          <IconButton label={`${t("shell.language")}: ${locale === "en" ? "English" : "繁體中文"}`} onClick={() => setLocale(locale === "en" ? "zh-TW" : "en")}>
            <span className="flex items-center gap-0.5 text-[12px] font-semibold"><Languages size={16} />{locale === "en" ? "EN" : "中"}</span>
          </IconButton>
          {mounted && user ? (
            <DropdownMenu.Root>
              <DropdownMenu.Trigger className="flex items-center gap-2 rounded-full border border-line bg-surface py-1 pl-1 pr-2 hover:bg-surface-muted md:pr-3" aria-label={demoSwap(user.display_name, locale === "en")}>
                <span className="grid h-8 w-8 place-items-center rounded-full bg-brand-soft text-[13px] font-semibold text-brand">{demoSwap(user.display_name, locale === "en").slice(0, 1)}</span>
                <span className="hidden text-left leading-tight md:block">
                  <span className="block text-[13px] font-medium text-ink">{demoSwap(user.display_name, locale === "en")}</span>
                  <span className="block text-[11px] text-ink-3">{t(`shell.roles.${user.role}`)}</span>
                </span>
                <ChevronDown size={14} className="text-ink-3" />
              </DropdownMenu.Trigger>
              <DropdownMenu.Portal>
                <DropdownMenu.Content align="end" sideOffset={6} className="z-50 min-w-44 rounded-[12px] border border-line bg-surface p-1 shadow-card">
                  <DropdownMenu.Item className="cursor-pointer rounded-[8px] px-3 py-2 text-[14px] text-ink outline-none data-[highlighted]:bg-surface-muted" onSelect={() => router.push("/reports")}>
                    <span className="flex items-center gap-2"><FileText size={14} />{t("nav.reports")}</span>
                  </DropdownMenu.Item>
                  <DropdownMenu.Item className="cursor-pointer rounded-[8px] px-3 py-2 text-[14px] text-ink outline-none data-[highlighted]:bg-surface-muted" onSelect={() => router.push("/history")}>
                    <span className="flex items-center gap-2"><History size={14} />{t("nav.history")}</span>
                  </DropdownMenu.Item>
                  <DropdownMenu.Item className="cursor-pointer rounded-[8px] px-3 py-2 text-[14px] text-ink outline-none data-[highlighted]:bg-surface-muted" onSelect={() => router.push("/notifications")}>
                    <span className="flex items-center gap-2"><Bell size={14} />{t("nav.notifications")}</span>
                  </DropdownMenu.Item>
                  <DropdownMenu.Item className="cursor-pointer rounded-[8px] px-3 py-2 text-[14px] text-ink outline-none data-[highlighted]:bg-surface-muted" onSelect={() => router.push("/settings")}>
                    <span className="flex items-center gap-2"><Settings size={14} />{t("nav.settings")}</span>
                  </DropdownMenu.Item>
                  {user.role !== "investor" ? (
                    <DropdownMenu.Item className="cursor-pointer rounded-[8px] px-3 py-2 text-[14px] text-ink outline-none data-[highlighted]:bg-surface-muted" onSelect={() => router.push("/admin")}>
                      <span className="flex items-center gap-2"><Users size={14} />{t("nav.admin")}</span>
                    </DropdownMenu.Item>
                  ) : null}
                  <DropdownMenu.Item
                    className="flex cursor-pointer items-center gap-2 rounded-[8px] px-3 py-2 text-[14px] text-critical outline-none data-[highlighted]:bg-critical-soft"
                    onSelect={() => {
                      void signOut().then(() => router.push("/"));
                    }}
                  >
                    <LogOut size={14} /> {t("shell.logout")}
                  </DropdownMenu.Item>
                </DropdownMenu.Content>
              </DropdownMenu.Portal>
            </DropdownMenu.Root>
          ) : (
            <Link href="/login" className="flex h-10 items-center gap-2 rounded-full bg-ink px-4 text-[13px] font-medium text-bg hover:opacity-90">
              <LogIn size={15} /> {t("shell.login")}
            </Link>
          )}
        </div>
      </div>
    </header>
  );
}

function IconButton({ label, onClick, children }: { label: string; onClick: () => void; children: ReactNode }) {
  return (
    <button onClick={onClick} aria-label={label} title={label} className="grid h-10 w-10 place-items-center rounded-full bg-surface-muted text-ink-2 hover:text-ink">
      {children}
    </button>
  );
}

const CRUMB_KEYS: Record<string, string> = {
  dashboard: "nav.dashboard", simulator: "nav.simulation", margin: "nav.margin", "day-trading": "nav.dayTrading",
  scenarios: "nav.lab", "digital-twin": "nav.twin", legal: "nav.legal", rights: "nav.rights", timeline: "nav.timeline", disputes: "nav.disputes",
  contracts: "nav.contracts", "regulatory-monitor": "nav.regulatory", agents: "nav.agents", reports: "nav.reports",
  history: "nav.history", notifications: "nav.notifications", settings: "nav.settings", admin: "nav.admin",
};

function Breadcrumb() {
  const t = useTranslations();
  const parts = usePathname().split("/").filter(Boolean);
  if (parts.length < 2) return null;
  return (
    <nav aria-label="Breadcrumb" className="mb-3 flex flex-wrap items-center gap-1 text-[12px] text-ink-3">
      {parts.map((p, i) => {
        const href = "/" + parts.slice(0, i + 1).join("/");
        const label = CRUMB_KEYS[p] ? t(CRUMB_KEYS[p]) : p.length > 20 ? `${p.slice(0, 8)}…` : p;
        return (
          <span key={href} className="flex items-center gap-1">
            {i > 0 ? <ChevronRight size={12} aria-hidden /> : null}
            {i === parts.length - 1 ? <span className="text-ink-2">{label}</span> : <Link href={href} className="hover:text-ink">{label}</Link>}
          </span>
        );
      })}
    </nav>
  );
}

function MobileBottomNav() {
  const t = useTranslations("nav");
  const L = useL();
  const pathname = usePathname();
  const items = [
    { href: "/dashboard", label: t("dashboard"), icon: <LayoutGrid size={18} /> },
    { href: "/simulator/margin", label: t("margin"), icon: <TrendingDown size={18} /> },
    { href: "/scenarios", label: t("lab"), icon: <FlaskConical size={18} /> },
    { href: "/legal", label: t("legal"), icon: <BookOpenText size={18} /> },
  ];
  return (
    <nav aria-label={L("快速導覽", "Quick navigation")} className="fixed inset-x-0 bottom-0 z-30 grid grid-cols-4 border-t border-line bg-surface md:hidden">
      {items.map((it) => (
        <Link key={it.href} href={it.href} aria-current={pathname.startsWith(it.href) ? "page" : undefined} className={cn("flex flex-col items-center gap-0.5 py-2 text-[11px]", pathname.startsWith(it.href) ? "text-brand" : "text-ink-3")}>
          {it.icon}
          <span className="max-w-full truncate px-1">{it.label}</span>
        </Link>
      ))}
    </nav>
  );
}
