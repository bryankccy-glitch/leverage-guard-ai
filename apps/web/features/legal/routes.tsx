"use client";

import { useParams } from "next/navigation";
import { RegulationDetail } from "./Legal";

export function RegulationById() {
  const { id } = useParams<{ id: string }>();
  return <RegulationDetail id={decodeURIComponent(id)} />;
}
