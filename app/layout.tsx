import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Futures Testnet Trader",
  description: "Binance Futures Testnet trading interface",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

