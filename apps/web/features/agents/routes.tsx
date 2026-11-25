"use client";

import { useParams } from "next/navigation";
import { AgentRunView } from "./AgentsCenter";

export function AgentRunById() {
  const { id } = useParams<{ id: string }>();
  return <AgentRunView id={id} />;
}
