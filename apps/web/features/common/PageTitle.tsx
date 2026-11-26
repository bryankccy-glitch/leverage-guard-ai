"use client";

import { useTranslations } from "next-intl";
import { useEffect, type ReactNode } from "react";
import { useIsEn } from "@/lib/i18n";
import { PageHeader } from "@/components/ui";

/** 頁面標題（i18n）。subtitleKey 優先；沒有就用 subtitle 原文。 */
export function PageTitle({ titleKey, subtitleKey, subtitle, subtitleEn, actions, badge }: { titleKey: string; subtitleKey?: string; subtitle?: string; subtitleEn?: string; actions?: ReactNode; badge?: ReactNode }) {
  const t = useTranslations();
  const isEn = useIsEn();
  const title = t(titleKey);
  // 語系只存在瀏覽器端，伺服器端 metadata 無法得知，所以由這裡更新分頁標題
  useEffect(() => {
    document.title = `${title}${isEn ? " | " : "｜"}LeverageGuard AI`;
  }, [title, isEn]);
  return <PageHeader title={title} subtitle={subtitleKey ? t(subtitleKey) : isEn && subtitleEn ? subtitleEn : subtitle} actions={actions} badge={badge} />;
}
