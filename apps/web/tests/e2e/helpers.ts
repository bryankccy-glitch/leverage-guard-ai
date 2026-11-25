import type { Page } from "@playwright/test";

export const API = process.env.API_URL ?? "http://127.0.0.1:8810";

export async function loginAs(page: Page, who: "investor" | "reviewer" | "admin" | "investor2" = "investor") {
  await page.goto("/login");
  await page.getByRole("button", { name: new RegExp(`${who}@demo`) }).click();
  await page.waitForURL(/\/(dashboard|admin)/);
}
