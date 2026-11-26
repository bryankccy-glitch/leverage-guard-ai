"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { LogIn, ShieldCheck, UserRound, Users } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useL } from "@/lib/i18n";
import { LogoHorizontal } from "@/components/brand/Logo";
import { Badge, Card, ErrorState, LoadingBlock, Notice } from "@/components/ui";
import { api } from "@/lib/api";
import { accountToEmail, authConfig, supabaseClient } from "@/lib/supabase";
import { useAuth, type User } from "@/stores/auth";

export function Login({ register }: { register?: boolean }) {
  const t = useTranslations();
  const L = useL();
  const router = useRouter();
  const setSession = useAuth((s) => s.setSession);
  const cfg = useQuery({ queryKey: ["auth-config"], queryFn: authConfig });
  const [account, setAccount] = useState("");
  const [password, setPassword] = useState("");
  // 帳號密碼登入（AUTH_MODE=supabase）：帳號對應 <帳號>@login_domain，憑證由 Supabase Auth 簽發、後端驗證
  const pwLogin = useMutation({
    mutationFn: async () => {
      const client = await supabaseClient();
      if (!client || !cfg.data?.login_domain) throw new Error(L("登入服務尚未設定完成", "Sign-in is not configured yet"));
      const { data, error } = await client.auth.signInWithPassword({ email: accountToEmail(account, cfg.data.login_domain), password });
      if (error || !data.session) {
        const m = (error?.message ?? "").toLowerCase();
        throw new Error(m.includes("rate") ? L("嘗試太多次，請稍後再試", "Too many attempts. Please try again later.")
          : m.includes("invalid") ? L("帳號或密碼錯誤", "Incorrect account or password")
          : L("登入失敗，請稍後再試", "Sign-in failed. Please try again."));
      }
      useAuth.setState({ token: data.session.access_token });
      const me = await api<{ guest: boolean } & User>("/me");
      if (me.guest) throw new Error(L("登入失敗，請稍後再試", "Sign-in failed. Please try again."));
      return { token: data.session.access_token, user: { id: me.id, email: me.email, display_name: me.display_name, role: me.role } };
    },
    onSuccess: (r) => {
      setSession(r.token, r.user);
      router.push(r.user.role === "investor" ? "/dashboard" : "/admin");
    },
    onError: () => useAuth.getState().logout(),
  });
  const login = useMutation({
    mutationFn: (email: string) => api<{ access_token: string; user: User }>("/auth/dev/login", { body: { email }, auth: false }),
    onSuccess: (r) => {
      setSession(r.access_token, r.user);
      router.push(r.user.role === "investor" ? "/dashboard" : "/admin");
    },
  });
  const icon = (role: string) => (role === "system_admin" ? <ShieldCheck size={18} /> : role === "legal_reviewer" ? <Users size={18} /> : <UserRound size={18} />);
  return (
    <main id="main" className="grid min-h-screen place-items-center bg-bg px-4 py-10">
      <Card className="w-full max-w-md p-6">
        <Link href="/"><LogoHorizontal /></Link>
        <h1 className="mt-5 text-[22px] font-bold text-ink">{register ? t("auth.registerTitle") : t("auth.loginTitle")}</h1>
        {cfg.isLoading ? <LoadingBlock /> : cfg.error ? <ErrorState error={cfg.error} onRetry={() => cfg.refetch()} /> : cfg.data?.mode === "local" ? (
          <div className="mt-3 space-y-3">
            {register ? <Notice tone="blue">{t("auth.registerLocal")}</Notice> : null}
            <p className="text-[13px] text-ink-2">{t("auth.localMode")}</p>
            <ul className="space-y-2">
              {cfg.data.demo_accounts.map((a) => (
                <li key={a.email}>
                  <button onClick={() => login.mutate(a.email)} disabled={login.isPending} className="flex w-full items-center gap-3 rounded-[12px] border border-line px-4 py-3 text-left hover:border-brand hover:bg-surface-muted disabled:opacity-60">
                    <span className="grid h-10 w-10 place-items-center rounded-full bg-brand-soft text-brand">{icon(a.role)}</span>
                    <span className="min-w-0 flex-1">
                      <span className="block font-medium text-ink">{a.label}</span>
                      <span className="block truncate text-[12px] text-ink-3">{a.email}</span>
                    </span>
                    <Badge tone="unknown">{t(`shell.roles.${a.role}`)}</Badge>
                    <LogIn size={16} className="text-ink-3" aria-label={t("auth.loginAs")} />
                  </button>
                </li>
              ))}
            </ul>
            {login.error ? <ErrorState error={login.error} /> : null}
          </div>
        ) : register ? (
          <Notice tone="blue" title={L("不開放自行註冊", "Self sign-up is closed")}>
            {L("帳號由管理員建立。需要帳號請聯絡管理員；已有帳號請到登入頁。", "Accounts are created by the administrator. Contact them for an account, or go to the sign-in page if you already have one.")}
            <Link href="/login" className="mt-2 block text-blue hover:underline">{t("auth.loginTitle")}</Link>
          </Notice>
        ) : (
          <form
            className="mt-4 space-y-3"
            onSubmit={(e) => {
              e.preventDefault();
              pwLogin.mutate();
            }}
          >
            <label className="block text-[13px] font-medium text-ink">
              {L("帳號", "Account")}
              <input value={account} onChange={(e) => setAccount(e.target.value)} autoComplete="username" autoFocus required
                placeholder={L("例如 bryan", "e.g. bryan")}
                className="mt-1 w-full rounded-[10px] border border-line bg-surface px-3 py-2 text-[15px] text-ink focus:border-brand focus:outline-none" />
            </label>
            <label className="block text-[13px] font-medium text-ink">
              {L("密碼", "Password")}
              <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" required
                className="mt-1 w-full rounded-[10px] border border-line bg-surface px-3 py-2 text-[15px] text-ink focus:border-brand focus:outline-none" />
            </label>
            {pwLogin.error ? <p role="alert" className="text-[13px] text-critical">{pwLogin.error.message}</p> : null}
            <button type="submit" disabled={pwLogin.isPending || !account.trim() || !password}
              className="flex w-full items-center justify-center gap-2 rounded-[10px] bg-brand px-4 py-2.5 text-[15px] font-medium text-white hover:opacity-90 disabled:opacity-60">
              <LogIn size={16} /> {pwLogin.isPending ? L("登入中…", "Signing in…") : L("登入", "Sign in")}
            </button>
          </form>
        )}
        <div className="mt-5 border-t border-line pt-4 text-center">
          <Link href="/simulator/margin" className="text-[14px] text-blue hover:underline">{t("auth.continueGuest")}</Link>
        </div>
        <p className="mt-3 text-center text-[12px] text-ink-3">{t("common.notAdvice")}</p>
      </Card>
    </main>
  );
}
