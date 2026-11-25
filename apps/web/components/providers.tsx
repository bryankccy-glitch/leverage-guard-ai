"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { NextIntlClientProvider } from "next-intl";
import { ThemeProvider } from "next-themes";
import { useEffect, useState, type ReactNode } from "react";
import en from "@/messages/en.json";
import zh from "@/messages/zh-TW.json";
import { rehydrateStores, useUI } from "@/stores/auth";

const MESSAGES = { "zh-TW": zh, en } as const;

export function Providers({ children }: { children: ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: { queries: { staleTime: 30_000, retry: 1, refetchOnWindowFocus: false } },
      }),
  );
  const locale = useUI((s) => s.locale);
  useEffect(() => rehydrateStores(), []);
  useEffect(() => {
    document.documentElement.lang = locale === "en" ? "en" : "zh-Hant-TW";
  }, [locale]);
  return (
    <ThemeProvider attribute="class" defaultTheme="light" enableSystem disableTransitionOnChange>
      <NextIntlClientProvider locale={locale} messages={MESSAGES[locale]} timeZone="Asia/Taipei">
        <QueryClientProvider client={client}>{children}</QueryClientProvider>
      </NextIntlClientProvider>
    </ThemeProvider>
  );
}
