"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";

const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000";
const buildApiUrl = (path: string): string =>
  `${backendUrl.replace(/\/+$/, "")}/${path.replace(/^\/+/, "")}`;

type ContactCategory = "pytanie" | "sugestia" | "nowa_funkcja" | "blad" | "inne";

const categoryLabels: Record<ContactCategory, string> = {
  pytanie: "Pytanie",
  sugestia: "Sugestia",
  nowa_funkcja: "Propozycja nowej funkcji",
  blad: "Zgłoszenie błędu",
  inne: "Inne",
};

export default function KontaktPage() {
  const [email, setEmail] = useState("");
  const [category, setCategory] = useState<ContactCategory>("pytanie");
  const [message, setMessage] = useState("");
  const [rodoConsent, setRodoConsent] = useState(false);
  const [honeypot, setHoneypot] = useState("");

  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const canSubmit =
    email.trim().length >= 5 &&
    message.trim().length >= 10 &&
    rodoConsent &&
    !submitting;

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    setSuccess(null);

    try {
      const response = await fetch(buildApiUrl("/api/contact"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: email.trim(),
          category,
          message: message.trim(),
          rodo_consent: rodoConsent,
          turnstile_token: null,
          honeypot: honeypot || null,
        }),
      });

      if (!response.ok) {
        const details = await response.json().catch(() => null);
        throw new Error(
          details?.detail ?? `Wysłanie formularza nie powiodło się (${response.status}).`
        );
      }

      const data = await response.json();
      setSuccess(data.message ?? "Wiadomość wysłana pomyślnie!");
      setEmail("");
      setMessage("");
      setRodoConsent(false);
      setCategory("pytanie");
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Nieznany błąd podczas wysyłania."
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="app-shell page-shell">
      <Link href="/" className="back-link">
        ← Powrót do porównywarki
      </Link>

      <article className="card section-card page-content">
        <h1>Kontakt</h1>
        <p className="muted">
          Masz pytanie, sugestię lub pomysł na nową funkcję? Napisz do nas
          korzystając z poniższego formularza. Odpowiemy najszybciej jak to
          możliwe.
        </p>

        {success && (
          <div className="contact-success">
            <strong>✓</strong> {success}
          </div>
        )}

        {error && (
          <div className="contact-error">
            <strong>Błąd:</strong> {error}
          </div>
        )}

        <form onSubmit={onSubmit} className="contact-form">
          <label className="form-field">
            <span className="form-label">
              Adres e-mail <span className="required">*</span>
            </span>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="jan.kowalski@example.com"
              required
              minLength={5}
              maxLength={254}
              autoComplete="email"
            />
          </label>

          <label className="form-field">
            <span className="form-label">
              Kategoria <span className="required">*</span>
            </span>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value as ContactCategory)}
            >
              {Object.entries(categoryLabels).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>

          <label className="form-field">
            <span className="form-label">
              Treść wiadomości <span className="required">*</span>
            </span>
            <textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="Opisz swoje pytanie, sugestię lub propozycję..."
              required
              minLength={10}
              maxLength={5000}
              rows={6}
            />
            <span className="form-hint">
              {message.length} / 5000 znaków (min. 10)
            </span>
          </label>

          {/* Honeypot field – hidden from real users, filled by bots */}
          <div className="hp-field" aria-hidden="true" tabIndex={-1}>
            <label>
              Nie wypełniaj tego pola
              <input
                type="text"
                value={honeypot}
                onChange={(e) => setHoneypot(e.target.value)}
                tabIndex={-1}
                autoComplete="off"
              />
            </label>
          </div>

          <label className="form-checkbox">
            <input
              type="checkbox"
              checked={rodoConsent}
              onChange={(e) => setRodoConsent(e.target.checked)}
              required
            />
            <span>
              Wyrażam zgodę na przetwarzanie moich danych osobowych (adres
              e-mail) w celu obsługi niniejszego zgłoszenia, zgodnie z{" "}
              <Link href="/regulamin">Regulaminem</Link> i przepisami RODO
              (Rozporządzenie Parlamentu Europejskiego i Rady (UE) 2016/679).
              Dane będą przetwarzane wyłącznie w celu udzielenia odpowiedzi na
              zgłoszenie i nie będą udostępniane podmiotom trzecim.{" "}
              <span className="required">*</span>
            </span>
          </label>

          <button type="submit" disabled={!canSubmit} className="submit-btn">
            {submitting ? "Wysyłanie..." : "Wyślij wiadomość"}
          </button>
        </form>
      </article>
    </main>
  );
}
