"use client";

import { useL } from "@/lib/i18n";

/** 鍵盤使用者按 Tab 才會看到的「跳到主要內容」連結，依語系顯示。 */
export function SkipLink() {
  const L = useL();
  return (
    <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-50 focus:rounded-lg focus:bg-surface focus:px-3 focus:py-2">
      {L("跳到主要內容", "Skip to main content")}
    </a>
  );
}
