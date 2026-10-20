import "./globals.css";
import type { Metadata } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "Nie głosuj — Porównywarka programów partii politycznych",
  description: "Dopóki nie poznasz programu. Porównuj stanowiska partii na podstawie źródeł."
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="pl">
      <body>{children}</body>
    </html>
  );
}
