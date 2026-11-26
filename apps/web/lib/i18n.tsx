"use client";

import { useLocale } from "next-intl";
import type { ReactNode } from "react";

/**
 * 雙語小工具：寫死在元件裡的文字用 L("中文", "English")，中文原句不搬家、不會改壞。
 * 介面通用詞仍放 messages/*.json（next-intl）。
 */
// 語系一律從 next-intl 讀取（與 t() 同一來源、同一更新時機），避免 Suspense 內 hydration 不一致
export function useL() {
  const locale = useLocale();
  return (zh: string, en: string) => (locale === "en" ? en : zh);
}

export function useIsEn() {
  return useLocale() === "en";
}

/** 伺服器元件（靜態頁）用：兩種語言的 JSX 都傳進來，由瀏覽器端依語系挑一個。 */
export function Bi({ zh, en }: { zh: ReactNode; en: ReactNode }) {
  return <>{useIsEn() ? en : zh}</>;
}

/**
 * 法規英文名稱。前三部取自全國法規資料庫英文版名稱；其餘為本平台翻譯（非官方）。
 * 法條原文一律保留中文（系統逐字比對官方條文），不顯示非官方譯文當作條文。
 */
const LAW_EN: Record<string, string> = {
  "moj:G0400001": "Securities and Exchange Act",
  "moj:G0340078": "Securities Transaction Tax Act",
  "moj:G0380226": "Financial Consumer Protection Act",
  "moj:G0400005": "Regulations Governing Securities Finance Enterprises",
  "moj:G0400009": "Criteria Governing Securities Eligible for Margin Purchase and Short Sale",
  "moj:G0400024": "Regulations Governing Margin Purchase and Short Sale by Securities Firms",
  "twse:FL007121": "TWSE Operating Rules for Securities Firms Handling Margin Purchase and Short Sale",
  "twse:FL071871": "TWSE Operating Rules for Day Trading of Securities",
};
const LAW_EN_BY_TITLE: Record<string, string> = {
  證券交易法: LAW_EN["moj:G0400001"],
  證券交易稅條例: LAW_EN["moj:G0340078"],
  金融消費者保護法: LAW_EN["moj:G0380226"],
  證券金融事業管理規則: LAW_EN["moj:G0400005"],
  有價證券得為融資融券標準: LAW_EN["moj:G0400009"],
  證券商辦理有價證券買賣融資融券管理辦法: LAW_EN["moj:G0400024"],
  證券商辦理有價證券買賣融資融券業務操作辦法: LAW_EN["twse:FL007121"],
  有價證券當日沖銷交易作業辦法: LAW_EN["twse:FL071871"],
};

export function lawTitle(sourceKey: string | undefined, zhTitle: string, isEn: boolean) {
  if (!isEn) return zhTitle;
  return (sourceKey && LAW_EN[sourceKey]) || LAW_EN_BY_TITLE[zhTitle] || zhTitle;
}

const AUTHORITY_EN: Record<string, string> = {
  全國法規資料庫: "Laws & Regulations Database (MOJ)",
  臺灣證券交易所: "Taiwan Stock Exchange",
  財政部: "Ministry of Finance",
  金融監督管理委員會: "Financial Supervisory Commission",
  官方原文: "Official text",
  臺灣證券交易所法規分享知識庫: "TWSE Regulations Knowledge Base",
};

export function authorityLabel(a: string, isEn: boolean) {
  return isEn ? (AUTHORITY_EN[a] ?? a) : a;
}

/** 「第54條」→「Art. 54」；「第2-2條」→「Art. 2-2」；「第54條之1」→「Art. 54-1」。 */
export function articleLabel(article: string, isEn: boolean) {
  if (!isEn) return article;
  const m = article.match(/^第\s*([\d-]+)\s*條(?:之\s*(\d+))?$/);
  if (!m) return article;
  return `Art. ${m[1]}${m[2] ? `-${m[2]}` : ""}`;
}

/** 示範名稱中英對照：值剛好是某個示範名稱時換成目前語系；使用者自己輸入的不動。 */
const DEMO_PAIRS: [string, string][] = [
  ["示範股票（虛構）", "Demo stock (fictional)"],
  ["示範股票 A（虛構）", "Demo stock A (fictional)"],
  ["示範股票 B（虛構）", "Demo stock B (fictional)"],
  ["我的模擬融資帳戶", "My simulated margin account"],
  ["示範投資人", "Demo investor"],
  ["示範投資人二", "Demo investor 2"],
  ["示範法律審查員", "Demo legal reviewer"],
  ["示範系統管理員", "Demo system admin"],
  ["模擬資產", "Simulated asset"],
  ["示範融資帳戶（模擬）", "Demo margin account (simulated)"],
  ["示範情境 A：融資追繳與剩餘債務", "Demo scenario A: margin call and residual debt"],
  ["示範情境 B：當沖未完成沖銷", "Demo scenario B: incomplete day-trade offset"],
  ["【示範】假設整戶擔保維持率追繳門檻由 130% 調整為 140%", "[Demo] Hypothetical change of the account-level call threshold from 130% to 140%"],
  ["臺灣證券交易所（虛構示範）", "Taiwan Stock Exchange (fictional demo)"],
];

export function demoSwap(value: string, isEn: boolean) {
  for (const [zh, en] of DEMO_PAIRS) if (value === zh || value === en) return isEn ? en : zh;
  return value;
}
