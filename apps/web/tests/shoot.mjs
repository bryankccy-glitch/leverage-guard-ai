// 開發用截圖：node tests/shoot.mjs <路徑> <輸出.png> [investor|reviewer|admin|guest] [dark] [寬] [高] [en]
import { chromium } from "@playwright/test";
const [path, out, who = "investor", theme = "light", w = "1440", h = "1100", lang = "zh"] = process.argv.slice(2);
const browser = await chromium.launch({ executablePath: process.env.CHROME_PATH ?? `${process.env.HOME}/Library/Caches/ms-playwright/chromium-1254/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing` });
const ctx = await browser.newContext({ viewport: { width: +w, height: +h }, colorScheme: theme === "dark" ? "dark" : "light" });
const page = await ctx.newPage();
const B = "http://localhost:3000";
if (who !== "guest") {
  const r = await fetch("http://127.0.0.1:8810/api/v1/auth/dev/login", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ email: `${who}@demo.leverageguard.local` }) });
  const j = await r.json();
  await page.goto(B + "/login");
  await page.evaluate(([tok, user]) => localStorage.setItem("lg-auth", JSON.stringify({ state: { token: tok, user }, version: 0 })), [j.access_token, j.user]);
}
await page.goto(B + "/login");
await page.evaluate(([t, l]) => { localStorage.setItem("theme", t); localStorage.setItem("lg-ui", JSON.stringify({ state: { locale: l === "en" ? "en" : "zh-TW", sidebarCollapsed: false }, version: 0 })); }, [theme, lang]);
const errors = [];
page.on("pageerror", (e) => errors.push(e.message));
page.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });
await page.goto(B + path, { waitUntil: "networkidle" });
await page.waitForTimeout(1500);
await page.screenshot({ path: out, fullPage: false });
if (errors.length) console.log("ERRORS:", errors.slice(0, 5).join("\n"));
await browser.close();
console.log("ok", out);
