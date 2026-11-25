import type { Metadata } from "next";
import { Login } from "@/features/auth/Login";

export const metadata: Metadata = { title: "建立帳號" };

export default function Page() {
  return <Login register />;
}
