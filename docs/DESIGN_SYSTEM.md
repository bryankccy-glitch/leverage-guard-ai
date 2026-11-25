# 設計系統

風格：Premium Consumer FinTech × Legal Intelligence。版面參考使用者提供的深色儀表板（左側獨立圓角側欄、膠囊搜尋、右上規則版本膠囊與頭像、主卡填色的 KPI 列、次要指標橫卡、2:1 主內容、底部區段），色彩與尺寸依需求規格。

## Tokens（`apps/web/app/globals.css`）

| Token | Light | Dark |
|---|---|---|
| bg / bg-2 | #F5F7FA / #EEF2F6 | #0B1220 / #101B2D |
| surface / surface-2 | #FFFFFF / #FFFFFF | #142136 / #1B2B42 |
| border | #DCE3EB | #29394F |
| text / 2 / 3 | #10243E / #475569 / #64748B | #F1F5F9 / #CBD5E1 / #94A3B8 |
| brand（teal） | #087F8C | #2DD4BF |
| blue | #2563EB | #60A5FA |
| hero（主 KPI 卡） | Navy #10243E | Teal #2DD4BF |
| Risk critical / high / warning / normal / unknown | #DC2626 / #EA580C / #B45309* / #047857* / #64748B | 對應較亮色 |
| Market up / down（台股紅漲綠跌） | #D6293B / #138A52 | #F87171 / #4ADE80 |

\* Warning 與 Normal 在淺色模式比規格稍深（#D97706→#B45309、#059669→#047857）；Text Muted 由 #64748B 調為 #5B6B80。標籤（12px）另用 `*-ink` 文字色：brand #066B76、blue #1D4ED8、critical #B91C1C、high #B4400A、warning #9A4A08、normal #036B4C、unknown #4F5D70。2026-11-26 以 WCAG 公式實算，各標籤文字與淡色底的對比為 4.84～5.92:1（原本最低 3.18:1）。

**Market Color 與 Risk Color 分開**：價格方向用紅漲綠跌，只出現在股價數字；法律風險用 Risk 色，而且一定搭配圖示與文字（`EventStatus` 元件），不只靠顏色。「正常」狀態文案不寫「安全」。

## 字型與尺寸

Geist（英數）、Noto Sans TC（中文）、Geist Mono；金融數字一律 `.num`（tabular numbers）。Display 44–48、H1 30–32、H2 24、H3 20、Body 15、Caption 12–13。間距 4／8／12／16／24／32／48／64。圓角：Button／Input 8、Card 12、Modal 16；側欄、頂部列、主 KPI 卡沿用參考版面的 16。

## 元件

`components/ui`：Button（primary、secondary、ghost、danger、pill、inverse）、Card、PageHeader、Badge、EventStatus、Field、Input、NumberField、Select、Skeleton、LoadingBlock、EmptyState、ErrorState（含 Request ID 與重試）、UnauthorizedState、Notice、SimBadge、NotAvailable。`features/common`：MetricList（每個數字可展開公式）、Timeline（法律責任時間軸）、CitationItem（官方引用＋驗證狀態）。

## 狀態

每個資料頁都有 Loading（skeleton）、Empty、Error（訊息、Request ID、重試）、Success、Unauthorized；權限不足時前端不發請求，後端仍會擋。

## 動態效果與無障礙

- Hover 150ms、時間軸淡入 200ms、情境播放；`prefers-reduced-motion` 時全部關閉。
- 跳到主要內容連結、`aria-current`、`aria-live` 進度、`aria-expanded`、所有圖表提供文字摘要與「資料表（無障礙）」。
- 鍵盤：所有互動元件都是原生按鈕、連結或 Radix 元件；`:focus-visible` 藍色外框。
- 手機：側欄改抽屜、底部導覽、表格水平捲動、滑桿可觸控。

## Logo

盾牌（保護）＋上升後回落的金融曲線（風險）＋天平橫桿（法律平衡）。檔案：`public/favicon.svg`、`app-icon.svg`、`logo-horizontal.svg`、`logo-mono.svg`、`og.svg`（社群預覽）；元件 `components/brand/Logo.tsx`。不使用法官槌、政府徽章或任何認證樣式。
