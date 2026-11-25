"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { LogIn, ShieldCheck, UserRound, Users } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { LogoHorizontal } from "@/components/brand/Logo";
import { Badge, Card, ErrorState, LoadingBlock, Notice } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth, type User } from "@/stores/auth";

type Config = { mode: "local" | "supabase"; demo_accounts: { email: string; label: string; role: User["role"] }[] };

export function Login({ register }: { register?: boolean }) {
  const t = useTranslations();
  const router = useRouter();
  const setSession = useAuth((s) => s.setSession);
  const cfg = useQuery({ queryKey: ["auth-config"], queryFn: () => api<Config>("/auth/config", { auth: false }) });
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
        ) : (
          <Notice tone="warning" title={t("auth.supabaseMode")}>
            已設定 AUTH_MODE=supabase。前端的 Supabase 登入元件需要 NEXT_PUBLIC_SUPABASE_URL 與 NEXT_PUBLIC_SUPABASE_ANON_KEY，目前尚未設定。
          </Notice>
        )}
        <div className="mt-5 border-t border-line pt-4 text-center">
          <Link href="/simulator/margin" className="text-[14px] text-blue hover:underline">{t("auth.continueGuest")}</Link>
        </div>
        <p className="mt-3 text-center text-[12px] text-ink-3">{t("common.notAdvice")}</p>
      </Card>
    </main>
  );
}
