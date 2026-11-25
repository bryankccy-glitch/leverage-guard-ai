"use client";

import { useParams } from "next/navigation";
import { ContractDetailView } from "./Contracts";

export function ContractById() {
  const { id } = useParams<{ id: string }>();
  return <ContractDetailView id={id} />;
}
