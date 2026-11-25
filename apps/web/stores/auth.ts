"use client";

import { useSyncExternalStore } from "react";
import { create } from "zustand";
import { persist } from "zustand/middleware";

export type Role = "investor" | "legal_reviewer" | "system_admin";
export type User = { id: string; email: string; display_name: string; role: Role };

type AuthState = {
  token: string | null;
  user: User | null;
  setSession: (token: string, user: User) => void;
  logout: () => void;
};

export const useAuth = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      setSession: (token, user) => set({ token, user }),
      logout: () => set({ token: null, user: null }),
    }),
    { name: "lg-auth", skipHydration: true },
  ),
);

type Locale = "zh-TW" | "en";
type UIState = {
  locale: Locale;
  sidebarCollapsed: boolean;
  setLocale: (l: Locale) => void;
  toggleSidebar: () => void;
};

export const useUI = create<UIState>()(
  persist(
    (set) => ({
      locale: "zh-TW",
      sidebarCollapsed: false,
      setLocale: (locale) => set({ locale }),
      toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
    }),
    { name: "lg-ui", skipHydration: true },
  ),
);

/** localStorage 只在瀏覽器端讀取：掛載後才 rehydrate，伺服器與瀏覽器第一次渲染一致。 */
export function rehydrateStores() {
  void useAuth.persist?.rehydrate();
  void useUI.persist?.rehydrate();
}

export function useHydrated(): boolean {
  // 伺服器端沒有 localStorage，persist API 不存在 → 視為尚未讀取
  return useSyncExternalStore(
    (cb) => useAuth.persist?.onFinishHydration(cb) ?? (() => {}),
    () => useAuth.persist?.hasHydrated() ?? false,
    () => false,
  );
}
