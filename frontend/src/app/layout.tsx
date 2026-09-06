import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "TRACE-X",
  description: "Fraud-linked crypto exchange identification from victim-reported wallets",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
