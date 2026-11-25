import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono, Noto_Sans_TC } from "next/font/google";
import { Providers } from "@/components/providers";
import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });
const notoTC = Noto_Sans_TC({ variable: "--font-noto-tc", subsets: ["latin"], weight: ["400", "500", "700"], preload: false });

export const metadata: Metadata = {
  title: { default: "LeverageGuard AI｜金融交易風險與法律責任情境模擬", template: "%s｜LeverageGuard AI" },
  description: "看見風險，理解責任，掌握權益。融資與當沖的財務風險、法律責任與契約條款互動式模擬。不提供投資建議。",
  icons: { icon: "/favicon.svg" },
  openGraph: { images: ["/og.svg"], title: "LeverageGuard AI", description: "Know the Risk. Understand Your Rights." },
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#F5F7FA" },
    { media: "(prefers-color-scheme: dark)", color: "#0B1220" },
  ],
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="zh-Hant-TW" suppressHydrationWarning className={`${geistSans.variable} ${geistMono.variable} ${notoTC.variable} h-full antialiased`}>
      <body className="min-h-full">
        <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-50 focus:rounded-lg focus:bg-surface focus:px-3 focus:py-2">
          跳到主要內容
        </a>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
