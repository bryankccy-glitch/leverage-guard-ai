"use client";

// AUTH_MODE=supabase 時的帳號密碼登入（做法同 ImportGuard）：
// 使用者輸入帳號（例如 bryan），對應 Supabase Auth 的 bryan@<login_domain>；輸入完整 email 則直接使用。
// 權限仍由後端驗證憑證＋資料庫 RLS 決定，這裡只負責取得與續期 Supabase 的登入憑證。
import type { SupabaseClient } from "@supabase/supabase-js";
import { useAuth } from "@/stores/auth";

export type AuthConfig = {
  mode: "local" | "supabase";
  demo_mode: boolean;
  demo_accounts: { email: string; label: string; role: "investor" | "legal_reviewer" | "system_admin" }[];
  supabase_url: string | null;
  supabase_anon_key: string | null;
  login_domain: string | null;
};

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8810";

let configPromise: Promise<AuthConfig> | null = null;
let clientPromise: Promise<SupabaseClient | null> | null = null;

/** 登入設定是公開資料，整個分頁只抓一次（不能用 api()，否則 api() 取憑證時會互相等待）。 */
export function authConfig(): Promise<AuthConfig> {
  configPromise ??= fetch(`${API_URL}/api/v1/auth/config`)
    .then((r) => {
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      return r.json() as Promise<AuthConfig>;
    })
    .catch((e) => {
      configPromise = null; // 失敗時下次重試
      throw e;
    });
  return configPromise;
}

/** supabase 模式才建立 client；local 模式回傳 null。 */
export function supabaseClient(): Promise<SupabaseClient | null> {
  clientPromise ??= (async () => {
    const cfg = await authConfig();
    if (cfg.mode !== "supabase" || !cfg.supabase_url || !cfg.supabase_anon_key) return null;
    const { createClient } = await import("@supabase/supabase-js");
    const client = createClient(cfg.supabase_url, cfg.supabase_anon_key, {
      auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: false, storageKey: "lg-supabase" },
    });
    // 自動續期後把新憑證同步到 useAuth；在別的分頁登出時這裡也登出
    client.auth.onAuthStateChange((event, session) => {
      if (session?.access_token && useAuth.getState().token) useAuth.setState({ token: session.access_token });
      if (event === "SIGNED_OUT") useAuth.getState().logout();
    });
    return client;
  })().catch((e) => {
    clientPromise = null;
    throw e;
  });
  return clientPromise;
}

/** 帳號 → 登入用 email。 */
export function accountToEmail(account: string, domain: string): string {
  const name = account.trim().toLowerCase();
  return name.includes("@") ? name : `${name}@${domain}`;
}

/** 呼叫 API 前取得目前的憑證：supabase 模式取（必要時自動續期的）最新憑證，最多等 4 秒，否則用已存的。 */
export async function currentToken(): Promise<string | null> {
  const stored = useAuth.getState().token;
  if (!stored) return stored;
  try {
    const client = await supabaseClient();
    if (!client) return stored;
    const fresh = client.auth.getSession().then((r) => r.data.session?.access_token ?? null);
    const fallback = new Promise<string | null>((resolve) => setTimeout(() => resolve(stored), 4000));
    const token = await Promise.race([fresh, fallback]);
    if (token && token !== stored) useAuth.setState({ token });
    return token ?? stored;
  } catch {
    return stored;
  }
}

/** 登出：同時清掉 Supabase 的工作階段（local 模式只清前端狀態）。 */
export async function signOut(): Promise<void> {
  try {
    const client = clientPromise ? await clientPromise : null;
    await client?.auth.signOut();
  } catch {
    /* 網路失敗也要清掉本機狀態 */
  }
  useAuth.getState().logout();
}
