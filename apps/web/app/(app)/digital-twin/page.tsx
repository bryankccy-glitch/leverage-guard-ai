import type { Metadata } from "next";
import { PageTitle } from "@/features/common/PageTitle";
import { DigitalTwin } from "@/features/twin/Twin";

export const metadata: Metadata = { title: "金融法律數位分身" };

export default function Page() {
  return (
    <>
      <PageTitle titleKey="twin.title" subtitleKey="twin.subtitle" />
      <DigitalTwin />
    </>
  );
}
