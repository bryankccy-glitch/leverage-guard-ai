"use client";

import { useParams } from "next/navigation";
import { ScenarioDetail } from "./Lab";

export function ScenarioDetailById() {
  const { id } = useParams<{ id: string }>();
  return <ScenarioDetail id={id} />;
}
