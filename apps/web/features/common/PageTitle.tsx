"use client";

import { useTranslations } from "next-intl";
import type { ReactNode } from "react";
import { PageHeader } from "@/components/ui";

/** 頁面標題（i18n）。subtitleKey 優先；沒有就用 subtitle 原文。 */
export function PageTitle({ titleKey, subtitleKey, subtitle, actions, badge }: { titleKey: string; subtitleKey?: string; subtitle?: string; actions?: ReactNode; badge?: ReactNode }) {
  const t = useTranslations();
  return <PageHeader title={t(titleKey)} subtitle={subtitleKey ? t(subtitleKey) : subtitle} actions={actions} badge={badge} />;
}
