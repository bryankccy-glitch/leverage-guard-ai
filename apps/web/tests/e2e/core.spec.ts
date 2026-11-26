import { expect, test } from "@playwright/test";
import { loginAs } from "./helpers";

test("訪客不用登入就能在首頁拖動股價並看到法律事件變化", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("你知道交易可能虧多少");
  const slider = page.getByRole("slider", { name: "模擬股價" });
  await slider.focus();
  for (let i = 0; i < 30; i++) await page.keyboard.press("ArrowLeft");
  await expect(page.getByText("維持率低於 130%：符合補繳通知條件").locator("..")).toContainText("模擬中觸發");
});

test("融資模擬：拖動滑桿後維持率與補繳差額同步更新，並顯示官方條文", async ({ page }) => {
  await page.goto("/simulator/margin");
  await page.getByRole("button", { name: "−30%（70）" }).click();
  await expect(page.getByText("116.67%").first()).toBeVisible();
  // 技術資訊收進「計算假設」：等後端驗證完成，再展開確認有後端正式計算
  await expect(page.getByText("等待後端驗證…")).toHaveCount(0, { timeout: 15000 });
  await page.getByRole("button", { name: "展開", exact: true }).last().click();
  await expect(page.getByText(/後端正式計算/)).toBeVisible();
  await expect(page.getByText("整戶擔保維持率追繳門檻").first()).toBeVisible();
  await expect(page.getByText("引用已比對官方原文").first()).toBeVisible();
  // 詳細計算結果預設收合（評審回饋）：先展開再點數字看公式
  await page.getByRole("button", { name: "展開", exact: true }).first().click();
  await page.getByRole("button", { name: /估計補繳差額/ }).click();
  await expect(page.getByText(/融資借款 −（價格 × 股數 × 融資比率）/)).toBeVisible();
});

test("當沖模擬：部分沖銷顯示未沖銷股數、資金缺口與時間軸", async ({ page }) => {
  await page.goto("/simulator/day-trading");
  await page.getByRole("button", { name: "交割資金不足" }).click();
  await expect(page.getByText("未沖銷部分轉一般交割").first()).toBeVisible({ timeout: 15000 });
  await expect(page.getByText("估計交割資金不足").first()).toBeVisible();
  await expect(page.getByText(/不代表已經違約/)).toBeVisible();
});

test("極端情境實驗室：推演並逐步播放時間軸", async ({ page }) => {
  await page.goto("/scenarios/new?preset=residual_debt");
  await expect(page.getByText("剩餘債務：通知補足").first()).toBeVisible({ timeout: 20000 });
  await page.getByRole("button", { name: "上一步" }).click();
  await expect(page.getByText(/Step \d+ \/ \d+/)).toBeVisible();
});

test("法律搜尋：口語「斷頭」找到證交所第 55 條", async ({ page }) => {
  await page.goto("/legal/search?q=" + encodeURIComponent("斷頭"));
  await expect(page.getByRole("link", { name: /融資融券業務操作辦法 第55條/ }).first()).toBeVisible({ timeout: 20000 });
});

test("登入、上傳示範契約並看到條款", async ({ page }) => {
  await loginAs(page, "investor2");
  await page.goto("/contracts/upload");
  await page.getByRole("button", { name: "使用虛構示範契約" }).click();
  await page.waitForURL(/\/contracts\/[0-9a-f-]{36}/);
  await expect(page.getByText("第四條").first()).toBeVisible({ timeout: 60000 });
  await expect(page.getByText("維持率條件").first()).toBeVisible();
  await page.getByRole("button", { name: "刪除" }).click({ trial: true });
});

test("深淺色與語言切換", async ({ page }) => {
  await page.goto("/simulator/margin");
  await page.getByRole("button", { name: "切換深淺色" }).click();
  await expect(page.locator("html")).toHaveClass(/dark/);
  await page.getByRole("button", { name: /語言/ }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Margin simulator");
});

test("手機版面：底部導覽與抽屜選單", async ({ browser }) => {
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 } });
  const page = await ctx.newPage();
  await page.goto("/simulator/margin");
  await expect(page.getByRole("navigation", { name: "快速導覽" })).toBeVisible();
  await page.getByRole("button", { name: "開啟選單" }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await ctx.close();
});

test("權限：投資人進入審查佇列看到權限提示", async ({ page }) => {
  await loginAs(page, "investor2");
  await page.goto("/admin/review-queue");
  await expect(page.getByText("需要法律審查員或系統管理員權限")).toBeVisible();
});
