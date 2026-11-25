import { expect, test } from "@playwright/test";
import { loginAs } from "./helpers";

// 需要本機千問；最久約 3 分鐘（逾時會改用規則模板，流程仍要能完成）
test("AI 分析 → 產生報告 → 匯出 PDF", async ({ page }) => {
  test.setTimeout(420_000);
  await loginAs(page, "investor2");
  await page.goto("/scenarios/new?preset=residual_debt");
  await page.getByRole("button", { name: "儲存" }).click();
  await page.waitForURL(/\/scenarios\/[0-9a-f-]{36}/);
  await page.getByRole("button", { name: "AI 白話分析" }).click();
  // 不論是即時執行或命中快取，完成後都會顯示驗證徽章
  await expect(page.getByText(/數字未被 AI 修改/)).toBeVisible({ timeout: 400_000 });
  await page.getByRole("button", { name: /產生報告（投資人版）/ }).click();
  await page.waitForURL(/\/reports\/[0-9a-f-]{36}/);
  await expect(page.getByText("未經專業審查").first()).toBeVisible();
  const [dl] = await Promise.all([page.waitForEvent("download"), page.getByRole("button", { name: "下載 PDF" }).click()]);
  expect(dl.suggestedFilename()).toMatch(/^LG-.*\.pdf$/);
});
