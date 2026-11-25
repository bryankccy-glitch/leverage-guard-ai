"use client";

import { useParams } from "next/navigation";
import { ReportView } from "./Reports";

export function ReportById() {
  const { id } = useParams<{ id: string }>();
  return <ReportView id={id} />;
}
