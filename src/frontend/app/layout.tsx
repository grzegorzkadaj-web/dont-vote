import "./globals.css";
import type { Metadata } from "next";
import type { ReactNode } from "react";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Nie głosuj — Porównywarka programów partii politycznych",
  description: "Dopóki nie poznasz programu. Porównuj stanowiska partii na podstawie źródeł."
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="pl">
      <body>
        {children}

        <footer className="site-footer">
          <div className="footer-inner">
            <div className="footer-brand">
              <span className="footer-logo" aria-hidden>NG</span>
              <span className="footer-brand-text">
                Nie głosuj — dopóki nie poznasz programu
              </span>
            </div>

            <nav className="footer-nav" aria-label="Stopka">
              <Link href="/manifest" className="footer-link">
                Manifest
              </Link>
              <Link href="/kontakt" className="footer-link">
                Kontakt
              </Link>
              <Link href="/regulamin" className="footer-link">
                Regulamin
              </Link>
            </nav>

            <p className="footer-copy">
              © {new Date().getFullYear()} Nie głosuj. Projekt edukacyjny
              — nie jest powiązany z żadną partią polityczną.
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}
