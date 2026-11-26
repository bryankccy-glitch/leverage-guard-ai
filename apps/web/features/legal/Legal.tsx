"use client";

import { useQuery } from "@tanstack/react-query";
import { BookOpenText, ExternalLink, FileText, Phone, Search } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";
import { articleLabel, authorityLabel, lawTitle, useIsEn, useL } from "@/lib/i18n";
import { Badge, Button, Card, CardHeader, EmptyState, ErrorState, Input, LoadingBlock, Notice, Select } from "@/components/ui";
import { api } from "@/lib/api";
import { cn, fmtDate } from "@/lib/format";
import { CitationItem, Timeline } from "../common/Timeline";
import type { Citation, ScenarioResult } from "../common/types";
import { Copilot } from "../copilot/Copilot";

type Doc = { id: string; source_key: string; official_title: string; authority: string; source_type: string; publisher: string; trading_types: string[]; official_url: string; version: string; retrieved_at: string; content_hash: string; article_count: number };
type Article = { article_id: string; article_number: string; chapter: string | null; content: string; source_key: string; official_title: string; authority: string; source_type: string; official_url: string; version: string; retrieved_at: string; highlights: string[] };

export function LegalHome() {
  const t = useTranslations("legal");
  const L = useL();
  const docs = useQuery({ queryKey: ["legal-docs"], queryFn: () => api<{ items: Doc[] }>("/legal/documents", { auth: false }) });
  return (
    <div className="space-y-5">
      <SearchBox />
      <div className="grid gap-4 md:grid-cols-3">
        <QuickLink href="/legal/rights" title={t("rightsTitle")} desc={t("rightsDesc")} />
        <QuickLink href="/legal/timeline" title={L("法律責任時間軸", "Legal responsibility timeline")} desc={t("timelineDesc")} />
        <QuickLink href="/legal/disputes" title={t("disputesTitle")} desc={t("disputesDesc")} />
      </div>
      <Card>
        <CardHeader title={t("documents")} desc={L("全部來自官方開放資料，保存版本、取得時間與內容雜湊", "All from official open data, with version, retrieval time and content hash kept")} />
        {docs.isLoading ? <LoadingBlock rows={5} /> : docs.error ? <ErrorState error={docs.error} onRetry={() => docs.refetch()} /> : <DocList docs={docs.data!.items} />}
      </Card>
    </div>
  );
}

export function DocList({ docs }: { docs: Doc[] }) {
  const t = useTranslations("legal");
  const isEn = useIsEn();
  const locale = useLocale();
  return (
    <ul className="divide-y divide-line px-5 pb-3">
      {docs.map((d) => (
        <li key={d.id} className="flex flex-wrap items-center gap-3 py-3">
          <FileText size={18} className="text-brand" aria-hidden />
          <Link href={`/legal/regulations/${d.source_key}`} className="min-w-0 flex-1 font-medium text-ink hover:text-brand">{lawTitle(d.source_key, d.official_title, isEn)}</Link>
          <Badge tone={d.source_type === "exchange_rule" ? "blue" : d.source_type === "statute" ? "brand" : "unknown"}>{t(`sourceType.${d.source_type}`)}</Badge>
          <span className="num text-[12px] text-ink-3">v{d.version} · {d.article_count} {t("articles")} · {t("retrievedAt")} {fmtDate(d.retrieved_at, locale)}</span>
        </li>
      ))}
    </ul>
  );
}

function QuickLink({ href, title, desc }: { href: string; title: string; desc: string }) {
  return (
    <Link href={href} className="rounded-[12px] border border-line bg-surface p-5 shadow-card hover:border-brand">
      <p className="font-semibold text-ink">{title}</p>
      <p className="mt-1 text-[13px] text-ink-2">{desc}</p>
    </Link>
  );
}

function SearchBox({ initial = "" }: { initial?: string }) {
  const t = useTranslations("legal");
  const L = useL();
  const router = useRouter();
  const [q, setQ] = useState(initial);
  return (
    <form role="search" onSubmit={(e) => { e.preventDefault(); if (q.trim()) router.push(`/legal/search?q=${encodeURIComponent(q.trim())}`); }} className="flex gap-2">
      <label htmlFor="legal-q" className="sr-only">{t("searchPlaceholder")}</label>
      <div className="relative flex-1">
        <Search size={17} className="absolute left-4 top-1/2 -translate-y-1/2 text-ink-3" aria-hidden />
        <Input id="legal-q" value={q} onChange={(e) => setQ(e.target.value)} placeholder={t("searchPlaceholder")} className="h-12 rounded-full pl-11" />
      </div>
      <Button type="submit" size="lg" className="rounded-full">{L("搜尋", "Search")}</Button>
    </form>
  );
}

export function LegalSearch() {
  const isEn = useIsEn();
  const t = useTranslations("legal");
  const L = useL();
  const params = useSearchParams();
  const q = params.get("q") ?? "";
  const [mode, setMode] = useState("hybrid");
  const [tt, setTt] = useState("");
  const res = useQuery({
    queryKey: ["legal-search", q, mode, tt],
    queryFn: () => api<{ items: { article: Article; score: number }[]; notes: string[] }>(`/legal/search?q=${encodeURIComponent(q)}&mode=${mode}${tt ? `&trading_type=${tt}` : ""}&limit=15`, { auth: false }),
    enabled: !!q,
  });
  return (
    <div className="space-y-4">
      <SearchBox key={q} initial={q} />
      <div className="flex flex-wrap gap-3">
        <Select aria-label={L("檢索模式", "Search mode")} value={mode} onChange={(e) => setMode(e.target.value)} className="w-40">
          {(["hybrid", "keyword", "semantic"] as const).map((m) => <option key={m} value={m}>{t(`mode.${m}`)}</option>)}
        </Select>
        <Select aria-label={t("filterType")} value={tt} onChange={(e) => setTt(e.target.value)} className="w-40">
          <option value="">{t("filterType")}{isEn ? ": " : "："}{t("all")}</option>
          <option value="margin">{L("融資", "Margin")}</option>
          <option value="day_trading">{L("當沖", "Day trading")}</option>
          <option value="general">{L("一般", "General")}</option>
        </Select>
      </div>
      {!q ? <Card><EmptyState icon={<BookOpenText size={28} />} title={t("searchPlaceholder")} /></Card> : res.isLoading ? <Card><LoadingBlock rows={5} /></Card> : res.error ? <Card><ErrorState error={res.error} /></Card> : (
        <>
          {res.data!.notes.map((n) => <Notice key={n} tone="unknown">{n}</Notice>)}
          {res.data!.items.length === 0 ? <Card><EmptyState title={L("找不到相關條文", "No matching articles")} desc={L("試試換個說法，例如「追繳」「處分其擔保品」「當日沖銷」", "Try other wording. The legal text is in Chinese, e.g. 追繳 (margin call), 處分其擔保品 (dispose of collateral), 當日沖銷 (day trading)")} /></Card> : (
            <ul className="space-y-3">
              {res.data!.items.map(({ article: a }) => <ArticleCard key={a.article_id} a={a} />)}
            </ul>
          )}
        </>
      )}
    </div>
  );
}

function highlight(text: string, terms: string[]) {
  if (!terms.length) return text;
  const re = new RegExp(`(${terms.map((x) => x.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|")})`, "g");
  return text.split(re).map((part, i) => (terms.includes(part) ? <mark key={i} className="rounded bg-warning-soft px-0.5 text-ink">{part}</mark> : part));
}

function ArticleCard({ a }: { a: Article }) {
  const t = useTranslations("legal");
  const isEn = useIsEn();
  return (
    <li className="rounded-[12px] border border-line bg-surface p-4 shadow-card">
      <div className="flex flex-wrap items-center gap-2">
        <Link href={`/legal/regulations/${a.source_key}#${a.article_number}`} className="font-semibold text-ink hover:text-brand">{lawTitle(a.source_key, a.official_title, isEn)} {articleLabel(a.article_number, isEn)}</Link>
        <Badge tone={a.source_type === "exchange_rule" ? "blue" : "brand"}>{t(`sourceType.${a.source_type}`)}</Badge>
        <span className="num text-[11px] text-ink-3">v{a.version}</span>
        <a href={a.official_url} target="_blank" rel="noopener noreferrer" className="ml-auto inline-flex items-center gap-1 text-[12px] text-blue hover:underline">{t("openOfficial")}<ExternalLink size={11} /></a>
      </div>
      {a.chapter ? <p lang="zh-Hant-TW" className="mt-0.5 text-[12px] text-ink-3">{a.chapter}</p> : null}
      <p lang="zh-Hant-TW" className="mt-2 whitespace-pre-line text-[14px] leading-7 text-ink-2">{highlight(a.content.length > 700 ? a.content.slice(0, 700) + "…" : a.content, a.highlights)}</p>
    </li>
  );
}

export function RegulationDetail({ id }: { id: string }) {
  const t = useTranslations("legal");
  const L = useL();
  const isEn = useIsEn();
  const locale = useLocale();
  const q = useQuery({ queryKey: ["legal-doc", id], queryFn: () => api<Doc & { articles: { id: string; article_number: string; chapter: string | null; content: string }[]; versions: { version: string; retrieved_at: string; content_hash: string; is_current: boolean }[] }>(`/legal/documents/${encodeURIComponent(id)}`, { auth: false }) });
  const [filter, setFilter] = useState("");
  if (q.isLoading) return <Card><LoadingBlock rows={8} /></Card>;
  if (q.error) return <Card><ErrorState error={q.error} /></Card>;
  const d = q.data!;
  const arts = d.articles
    .filter((a) => !filter || a.content.includes(filter) || a.article_number.includes(filter))
    .map((a, i, all) => ({ ...a, showChapter: !!a.chapter && a.chapter !== all[i - 1]?.chapter }));
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-[26px] font-bold text-ink">{lawTitle(d.source_key, d.official_title, isEn)}</h1>
        {isEn ? <p className="mt-1 text-[13px] text-ink-3">{d.official_title} · The article text below is the official original in Traditional Chinese; no English translation is shown as law.</p> : null}
        <div className="mt-2 flex flex-wrap items-center gap-2 text-[13px] text-ink-2">
          <Badge tone="brand">{t(`sourceType.${d.source_type}`)}</Badge>
          <span>{authorityLabel(d.authority, isEn)}</span>
          <span className="num">v{d.version}</span>
          <span className="num">{t("retrievedAt")} {fmtDate(d.retrieved_at, locale, true)}</span>
          <span className="num text-[11px] text-ink-3" title={L("內容雜湊（SHA-256）", "Content hash (SHA-256)")}>#{d.content_hash.slice(0, 12)}</span>
          <a href={d.official_url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-blue hover:underline">{t("openOfficial")}<ExternalLink size={12} /></a>
        </div>
      </div>
      <Input aria-label={L("在本法規中搜尋", "Search within this regulation")} placeholder={L("在本法規中搜尋（條號或關鍵字）", "Search this regulation (article number or Chinese keyword)")} value={filter} onChange={(e) => setFilter(e.target.value)} />
      <Card className="p-5">
        <ol className="space-y-4">
          {arts.map((a) => {
            return (
              <li key={a.id} id={a.article_number}>
                {a.showChapter ? <p lang="zh-Hant-TW" className="mb-2 mt-4 text-[13px] font-semibold text-brand">{a.chapter}</p> : null}
                <p className="font-semibold text-ink">{articleLabel(a.article_number, isEn)}</p>
                <p lang="zh-Hant-TW" className="whitespace-pre-line text-[14px] leading-7 text-ink-2">{a.content}</p>
              </li>
            );
          })}
        </ol>
      </Card>
      <Card>
        <CardHeader title={L("版本紀錄", "Version history")} />
        <ul className="px-5 pb-4 text-[13px]">{d.versions.map((v) => <li key={v.version} className="num py-1 text-ink-2">v{v.version} · {fmtDate(v.retrieved_at, locale, true)} · #{v.content_hash.slice(0, 12)} {v.is_current ? L("（目前）", "(current)") : ""}</li>)}</ul>
      </Card>
    </div>
  );
}

type RightItem = { description: string; rule_id: string; rule_name: string; trading_type: string; review_status: string; plain_language: string; citations: Citation[] };

export function RightsCenter({ kind = "both" }: { kind?: "rights" | "obligations" | "both" }) {
  const t = useTranslations();
  const L = useL();
  const [tt, setTt] = useState<string>("margin");
  const rights = useQuery({ queryKey: ["rights", tt], queryFn: () => api<{ items: RightItem[] }>(`/legal/rights?trading_type=${tt}`, { auth: false }) });
  const obligations = useQuery({ queryKey: ["obligations", tt], queryFn: () => api<{ items: RightItem[] }>(`/legal/obligations?trading_type=${tt}`, { auth: false }) });
  return (
    <div className="space-y-5">
      <div className="flex gap-2" role="tablist">
        {[["margin", L("融資交易", "Margin trading")], ["day_trading", L("當沖交易", "Day trading")], ["general", L("一般", "General")]].map(([k, l]) => (
          <button key={k} role="tab" aria-selected={tt === k} onClick={() => setTt(k)} className={cn("rounded-full px-4 py-1.5 text-[14px]", tt === k ? "bg-ink text-bg" : "border border-line text-ink-2")}>{l}</button>
        ))}
      </div>
      <Notice tone="unknown">{t("common.aiChecked")}{L("：以下內容由規則整理並附官方條文；規則已由 AI 逐條核對原文，但尚未經律師或金融法律專業人員審查，也不是正式法律意見。實際權利義務以你和券商的契約為準。", ": the items below are compiled from the rules with official legal text attached. AI has checked each rule against the original text, but no lawyer or financial-law professional has reviewed them, and they are not formal legal advice. Your actual rights and obligations follow your contract with the broker.")}</Notice>
      <div className={cn("grid gap-5", kind === "both" && "lg:grid-cols-2")}>
        {kind !== "obligations" ? <RightList title={t("timeline.investorRights")} q={rights} /> : null}
        {kind !== "rights" ? <RightList title={t("timeline.investorObligations")} q={obligations} /> : null}
      </div>
      <Card>
        <CardHeader title={t("legal.misconceptions")} />
        <ul className="space-y-3 p-5 text-[14px]">
          <Misconception wrong={L("追繳門檻股價就是斷頭價", "The call-threshold price is the liquidation price")} right={L("跌破門檻只是符合補繳通知條件；處分還要看通知送達、二個營業日補繳期限、期限當日維持率與契約約定。", "Falling below the threshold only meets the conditions for a top-up notice; disposal also depends on notice delivery, the two-business-day deadline, the ratio on the deadline and your contract.")} />
          <Misconception wrong={L("本金虧完就不用再付錢", "Once my principal is gone I owe nothing more")} right={L("處分所得不足清償借款時，券商會用帳戶其他款項抵充，仍不足會通知你補足；逾期未清償可能被申報違約（操作辦法第 55、81 條）。", "If disposal proceeds do not cover the loan, the broker offsets with other funds in your account and asks you to pay the rest; failing to repay in time may be reported as a default (operating rules Arts. 55 and 81).")} />
          <Misconception wrong={L("補繳就是把維持率補回 130%", "Topping up means bringing the ratio back to 130%")} right={L("應補繳的差額依第 54 條公式計算：融資金額 −（收盤價 × 股數 × 融資比率）−（抵繳品 × 融資比率）。", "The top-up amount follows the Art. 54 formula: margin loan − (closing price × shares × financing ratio) − (substitute collateral × financing ratio).")} />
          <Misconception wrong={L("當沖沒賣掉沒關係，隔天再賣", "If a day trade is not sold, I can just sell tomorrow")} right={L("只有相同數量的部分能相抵；沒賣掉的股數要以全額價金辦理交割。", "Only matching quantities offset; unsold shares must be settled at the full price.")} />
        </ul>
      </Card>
    </div>
  );
}

function RightList({ title, q }: { title: string; q: { isLoading: boolean; error: unknown; data?: { items: RightItem[] } } }) {
  const L = useL();
  return (
    <Card>
      <CardHeader title={title} />
      {q.isLoading ? <LoadingBlock /> : q.error ? <ErrorState error={q.error} /> : (
        <ul className="space-y-3 p-5">
          {q.data!.items.map((r, i) => (
            <li key={i} className="rounded-[12px] border border-line p-3">
              <p className="font-medium text-ink">{r.description}</p>
              <p className="mt-0.5 text-[12px] text-ink-3">{r.rule_name}</p>
              <details className="mt-1">
                <summary className="cursor-pointer text-[12px] text-blue">{L(`官方條文（${r.citations.length}）`, `Official text (${r.citations.length})`)}</summary>
                <ul className="mt-1 space-y-1.5">{r.citations.map((c, j) => <CitationItem key={j} c={c} />)}</ul>
              </details>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

function Misconception({ wrong, right }: { wrong: string; right: string }) {
  const L = useL();
  return (
    <li className="rounded-[12px] bg-surface-muted p-3">
      <p className="text-ink"><span className="mr-2 rounded bg-critical-soft px-1.5 text-[12px] text-critical">{L("誤解", "Myth")}</span>{wrong}</p>
      <p className="mt-1 text-ink-2"><span className="mr-2 rounded bg-normal-soft px-1.5 text-[12px] text-normal">{L("實際", "Fact")}</span>{right}</p>
    </li>
  );
}

export function LegalTimelinePage() {
  const L = useL();
  const [tt, setTt] = useState<"margin" | "day_trading">("margin");
  const body = tt === "margin"
    ? { asset_label: L("示範股票（虛構）", "Demo stock (fictional)"), buy_price: "100", quantity: "1000", financing_ratio: "0.6", annual_interest_rate: "0.0645", start_date: "2027-03-02", steps: [{ day: 0, price: "100" }, { day: 1, price: "80" }, { day: 2, price: "70" }, { day: 5, price: "50" }] }
    : { asset_label: L("示範股票（虛構）", "Demo stock (fictional)"), direction: "sell_first", buy_price: "100", buy_quantity: "1000", sell_price: "102", sell_quantity: "2000", trade_date: "2027-03-02", available_cash: "20000", assumed_buyback_price: "104", assumed_borrow_fee_rate: "0.02" };
  const q = useQuery({ queryKey: ["legal-timeline", tt], queryFn: () => api<ScenarioResult>(tt === "margin" ? "/calculate/scenario" : "/calculate/day-trading", { body, auth: false }) });
  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        {([["margin", L("融資：追繳 → 處分 → 剩餘債務", "Margin: call → disposal → residual debt")], ["day_trading", L("當沖：先賣後買未買回", "Day trade: sold first, not bought back")]] as const).map(([k, l]) => (
          <button key={k} onClick={() => setTt(k)} aria-pressed={tt === k} className={cn("rounded-full px-4 py-1.5 text-[14px]", tt === k ? "bg-ink text-bg" : "border border-line text-ink-2")}>{l}</button>
        ))}
      </div>
      <Notice tone="blue">{L("這是以示範參數（2027 年，已涵蓋證交所公告休市日）由規則引擎實際推演的時間軸；事件不一定依相同順序發生，實際以通知、期限與契約為準。", "This timeline was played out by the rule engine using demo inputs (2027, including TWSE-announced market holidays). Events may not happen in this order; actual notices, deadlines and your contract govern.")}</Notice>
      <Card className="p-4">{q.isLoading ? <LoadingBlock rows={8} /> : q.error ? <ErrorState error={q.error} /> : <Timeline nodes={q.data!.timeline} />}</Card>
    </div>
  );
}

export function DisputesPage() {
  const t = useTranslations("legal");
  const L = useL();
  return (
    <div className="space-y-5">
      <div className="grid gap-4 md:grid-cols-3">
        {[
          ["1", L("先向券商申訴", "Complain to the broker first"), L("金融消費者應先向金融服務業提出申訴；券商應於收受申訴之日起 30 日內處理並回覆。", "Financial consumers must first complain to the financial service provider; the broker must handle and reply within 30 days of receiving the complaint.")],
          ["2", L("申請評議", "Apply for mediation"), L("不接受處理結果，或券商逾期未處理，可在收到結果或期限屆滿之日起 60 日內，向爭議處理機構申請評議。", "If you reject the outcome or the broker misses the deadline, you can apply to the dispute resolution body within 60 days of the outcome or the deadline.")],
          ["3", L("保存資料", "Keep records"), L("追繳／處分通知、對帳單、處分成交明細、往來紀錄與契約。", "Margin call / disposal notices, statements, disposal trade details, correspondence and your contract.")],
        ].map(([n, title, desc]) => (
          <Card key={n} className="p-5">
            <p className="num text-[13px] font-semibold text-brand">STEP {n}</p>
            <p className="mt-1 font-semibold text-ink">{title}</p>
            <p className="mt-1 text-[13px] text-ink-2">{desc}</p>
          </Card>
        ))}
      </div>
      <Card>
        <CardHeader title={L("法律依據", "Legal basis")} />
        <div className="p-5">
          <CitationItem c={{ source_key: "moj:G0380226", official_title: "金融消費者保護法", authority: "全國法規資料庫", source_type: "statute", article_number: "第13條", quote: "金融消費者就金融消費爭議事件應先向金融服務業提出申訴，金融服務業應於收受申訴之日起三十日內為適當之處理", official_url: "https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode=G0380226", version: "20231206", retrieved_at: "", validated: true, validation_note: null }} />
        </div>
      </Card>
      <Card>
        <CardHeader title={t("disputesTitle")} desc={L("請先確認你的情況是否屬於該管道受理範圍；本平台不保證申訴或評議結果。", "First check whether your case falls within that channel's scope; this platform does not guarantee any complaint or mediation outcome.")} />
        <ul className="space-y-2 p-5 text-[14px]">
          <li className="flex items-center gap-2"><Phone size={15} className="text-brand" />{L("財團法人金融消費評議中心：", "Financial Ombudsman Institution: ")}<a className="text-blue underline" href="https://www.foi.org.tw/" target="_blank" rel="noopener noreferrer">www.foi.org.tw</a></li>
          <li className="flex items-center gap-2"><Phone size={15} className="text-brand" />{L("金融監督管理委員會證券期貨局：", "Securities and Futures Bureau, FSC: ")}<a className="text-blue underline" href="https://www.sfb.gov.tw/" target="_blank" rel="noopener noreferrer">www.sfb.gov.tw</a></li>
          <li className="flex items-center gap-2"><Phone size={15} className="text-brand" />{L("臺灣證券交易所：", "Taiwan Stock Exchange: ")}<a className="text-blue underline" href="https://www.twse.com.tw/" target="_blank" rel="noopener noreferrer">www.twse.com.tw</a></li>
        </ul>
      </Card>
      <Copilot context={{ trading_type: "margin", input: {} }} />
    </div>
  );
}
