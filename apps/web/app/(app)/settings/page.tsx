import type { Metadata } from "next";
import { PageTitle } from "@/features/common/PageTitle";
import { SettingsView } from "@/features/personal/Personal";

export const metadata: Metadata = { title: "設定" };

export default function Page() {
  return (
    <>
      <PageTitle titleKey="settings.title" />
      <SettingsView />
    </>
  );
}
