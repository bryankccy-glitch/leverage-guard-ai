// 巡檢：逐頁開啟，收集 console error / page error，存截圖。node tests/sweep.mjs [investor|reviewer|admin] [light|dark] [zh|en]
import { chromium } from "@playwright/test";
const [who = "investor", theme = "light", lang = "zh"] = process.argv.slice(2);
const CONTRACT = process.env.CONTRACT_ID ?? "";
const routes = ["/", "/about", "/how-it-works", "/legal-resources", "/privacy", "/terms", "/login", "/register",
  "/dashboard", "/simulator", "/simulator/margin", "/simulator/day-trading", "/simulator/short-selling", "/simulator/portfolio",
  "/digital-twin", "/digital-twin/accounts", "/digital-twin/positions", "/digital-twin/history",
  "/scenarios", "/scenarios/new", "/scenarios/compare",
  "/legal", "/legal/search?q=追繳", "/legal/regulations", "/legal/regulations/twse:FL007121", "/legal/rights", "/legal/obligations", "/legal/timeline", "/legal/disputes",
  "/contracts", "/contracts/upload", "/contracts/compare", ...(CONTRACT ? [`/contracts/${CONTRACT}`] : []),
  "/regulatory-monitor", "/regulatory-monitor/updates", "/regulatory-monitor/impact",
  "/agents", "/reports", "/history", "/notifications", "/settings",
  "/admin", "/admin/review-queue", "/admin/legal-rules", "/admin/rule-versions", "/admin/legal-sources", "/admin/knowledge-base",
  "/admin/agent-config", "/admin/evaluation", "/admin/system-health", "/admin/audit-logs", "/admin/users"];
const browser = await chromium.launch({ executablePath: `${process.env.HOME}/Library/Caches/ms-playwright/chromium-1254/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing` });
const ctx = await browser.newContext({ viewport: { width: 1440, height: 1000 }, colorScheme: theme });
const page = await ctx.newPage();
const B = process.env.WEB_URL ?? "http://localhost:3000";
const r = await fetch(`${process.env.API_URL ?? "http://127.0.0.1:8810"}/api/v1/auth/dev/login`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ email: `${who}@demo.leverageguard.local` }) });
const j = await r.json();
await page.goto(B + "/login");
await page.evaluate(([tok, user, t, l]) => { localStorage.setItem("lg-auth", JSON.stringify({ state: { token: tok, user }, version: 0 })); localStorage.setItem("theme", t); localStorage.setItem("lg-ui", JSON.stringify({ state: { locale: l === "en" ? "en" : "zh-TW", sidebarCollapsed: false }, version: 0 })); }, [j.access_token, j.user, theme, lang]);
let bad = 0;
for (const route of routes) {
  const errs = [];
  const onErr = (e) => errs.push(String(e.message ?? e));
  const onCon = (m) => { if (m.type() === "error" && !/favicon|Download the React DevTools|script tag/.test(m.text())) errs.push(m.text().slice(0, 200)); };
  page.on("pageerror", onErr); page.on("console", onCon);
  const resp = await page.goto(B + route, { waitUntil: "networkidle" }).catch((e) => ({ status: () => `ERR ${e.message}` }));
  await page.waitForTimeout(700);
  const status = resp?.status?.();
  const name = route.replace(/[\/?=:]/g, "_") || "_root";
  await page.screenshot({ path: `../../.tmp/shots/sweep/${who}_${theme}_${lang}${name}.png` });
  page.off("pageerror", onErr); page.off("console", onCon);
  const flag = status !== 200 || errs.length;
  if (flag) bad++;
  console.log(`${flag ? "✗" : "✓"} ${status} ${route}${errs.length ? "  → " + errs.slice(0, 2).join(" | ") : ""}`);
}
console.log(`完成：${routes.length} 頁，${bad} 頁有問題`);
await browser.close();
