import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Regulamin — Nie głosuj",
  description:
    "Regulamin serwisu Nie głosuj — informacje o źródłach danych, API, przetwarzaniu danych osobowych i zasadach korzystania.",
};

export default function RegulaminPage() {
  return (
    <main className="app-shell page-shell">
      <Link href="/" className="back-link">
        ← Powrót do porównywarki
      </Link>

      <article className="card section-card page-content">
        <h1>Regulamin</h1>
        <p className="muted">
          Ostatnia aktualizacja: październik 2026
        </p>

        <section className="regulamin-section">
          <h2>§ 1. Postanowienia ogólne</h2>
          <ol>
            <li>
              Niniejszy regulamin określa zasady korzystania z serwisu
              internetowego „Nie głosuj — dopóki nie poznasz programu"
              (dalej: „Serwis").
            </li>
            <li>
              Serwis ma charakter informacyjny i edukacyjny. Jego celem jest
              ułatwienie dostępu do treści programów partii politycznych oraz
              wyników głosowań sejmowych.
            </li>
            <li>
              Korzystanie z Serwisu jest bezpłatne i nie wymaga rejestracji.
            </li>
          </ol>
        </section>

        <section className="regulamin-section">
          <h2>§ 2. Źródła danych i zewnętrzne API</h2>
          <ol>
            <li>
              Serwis korzysta z następujących publicznych źródeł danych i
              interfejsów programistycznych (API):
              <ul>
                <li>
                  <strong>API Sejmu RP</strong> (
                  <a
                    href="https://api.sejm.gov.pl"
                    target="_blank"
                    rel="noreferrer"
                  >
                    api.sejm.gov.pl
                  </a>
                  ) — dane o posiedzeniach, głosowaniach, drukach sejmowych
                  i procesach legislacyjnych.
                </li>
                <li>
                  <strong>
                    Europejski Identyfikator Prawodawstwa (ELI)
                  </strong>{" "}
                  (
                  <a
                    href="https://api.sejm.gov.pl/eli"
                    target="_blank"
                    rel="noreferrer"
                  >
                    api.sejm.gov.pl/eli
                  </a>
                  ) — identyfikatory i metadane aktów prawnych
                  opublikowanych w Dzienniku Ustaw.
                </li>
                <li>
                  <strong>Internetowy System Aktów Prawnych (ISAP)</strong> (
                  <a
                    href="https://isap.sejm.gov.pl"
                    target="_blank"
                    rel="noreferrer"
                  >
                    isap.sejm.gov.pl
                  </a>
                  ) — pełne teksty aktów prawnych.
                </li>
                <li>
                  <strong>OpenAI API</strong> — model językowy GPT wykorzystywany
                  do generowania odpowiedzi porównawczych na podstawie treści
                  programów partii (technika RAG — Retrieval-Augmented
                  Generation).
                </li>
                <li>
                  <strong>Pinecone</strong> — wektorowa baza danych służąca do
                  semantycznego wyszukiwania fragmentów programów partyjnych.
                </li>
              </ul>
            </li>
            <li>
              Serwis nie jest oficjalnym serwisem Sejmu RP, żadnej partii
              politycznej ani żadnej innej instytucji publicznej. Treści
              prezentowane w Serwisie stanowią wynik automatycznego
              przetwarzania publicznie dostępnych dokumentów.
            </li>
            <li>
              Odpowiedzi generowane przez model AI mają charakter
              informacyjny i mogą zawierać uproszczenia. Zachęcamy do
              weryfikacji informacji w źródłach podlinkowanych przy każdej
              odpowiedzi.
            </li>
          </ol>
        </section>

        <section className="regulamin-section">
          <h2>§ 3. Przetwarzanie danych osobowych (RODO)</h2>
          <ol>
            <li>
              Administratorem danych osobowych jest właściciel Serwisu.
            </li>
            <li>
              Dane osobowe przetwarzane są wyłącznie w zakresie dobrowolnie
              podanym przez Użytkownika w{" "}
              <Link href="/kontakt">formularzu kontaktowym</Link> (adres
              e-mail, treść wiadomości).
            </li>
            <li>
              Podstawą prawną przetwarzania danych jest zgoda Użytkownika (art.
              6 ust. 1 lit. a RODO — Rozporządzenie Parlamentu Europejskiego
              i Rady (UE) 2016/679 z dnia 27 kwietnia 2016 r.).
            </li>
            <li>
              Dane przetwarzane są wyłącznie w celu:
              <ul>
                <li>udzielenia odpowiedzi na zgłoszenie kontaktowe,</li>
                <li>
                  rozpatrywania sugestii, propozycji nowych funkcji i zgłoszeń
                  błędów.
                </li>
              </ul>
            </li>
            <li>
              Dane nie będą udostępniane podmiotom trzecim, z wyjątkiem
              sytuacji wymaganych przepisami prawa.
            </li>
            <li>
              Dane przechowywane są w zaszyfrowanej lokalnej bazie danych
              Serwisu. Adresy IP są anonimizowane (haszowane jednokierunkowo)
              w celu ochrony przed nadużyciami.
            </li>
            <li>
              Użytkownik ma prawo do:
              <ul>
                <li>dostępu do swoich danych,</li>
                <li>sprostowania danych,</li>
                <li>usunięcia danych („prawo do bycia zapomnianym"),</li>
                <li>ograniczenia przetwarzania,</li>
                <li>cofnięcia zgody w dowolnym momencie,</li>
                <li>
                  wniesienia skargi do Prezesa Urzędu Ochrony Danych Osobowych
                  (PUODO).
                </li>
              </ul>
            </li>
            <li>
              W celu realizacji powyższych praw prosimy o kontakt przez{" "}
              <Link href="/kontakt">formularz kontaktowy</Link>.
            </li>
          </ol>
        </section>

        <section className="regulamin-section">
          <h2>§ 4. Ochrona przed nadużyciami</h2>
          <ol>
            <li>
              Formularz kontaktowy chroniony jest przed automatycznymi
              nadużyciami (spam, ataki DDoS) za pomocą:
              <ul>
                <li>
                  mechanizmu ograniczania częstotliwości zapytań (rate limiting),
                </li>
                <li>pola honeypot wykrywającego boty,</li>
                <li>
                  weryfikacji Cloudflare Turnstile (w środowisku produkcyjnym).
                </li>
              </ul>
            </li>
            <li>
              Serwis może stosować dodatkowe mechanizmy ochrony w warstwie
              infrastruktury (np. Cloudflare WAF, DDoS protection).
            </li>
          </ol>
        </section>

        <section className="regulamin-section">
          <h2>§ 5. Odpowiedzialność</h2>
          <ol>
            <li>
              Serwis dokłada wszelkich starań, aby prezentowane informacje
              były aktualne i zgodne ze źródłami. Nie ponosimy jednak
              odpowiedzialności za:
              <ul>
                <li>
                  błędy wynikające z automatycznego przetwarzania treści
                  przez modele AI,
                </li>
                <li>
                  czasową niedostępność zewnętrznych API (Sejm RP, OpenAI,
                  Pinecone),
                </li>
                <li>
                  decyzje podjęte przez Użytkownika na podstawie informacji
                  z Serwisu.
                </li>
              </ul>
            </li>
            <li>
              Treści w Serwisie nie stanowią porady prawnej, politycznej ani
              innej porady profesjonalnej.
            </li>
          </ol>
        </section>

        <section className="regulamin-section">
          <h2>§ 6. Postanowienia końcowe</h2>
          <ol>
            <li>
              Regulamin może być aktualizowany. O istotnych zmianach
              informujemy na stronie głównej Serwisu.
            </li>
            <li>
              W sprawach nieuregulowanych niniejszym regulaminem zastosowanie
              mają przepisy prawa polskiego, w szczególności Kodeks cywilny
              oraz RODO.
            </li>
          </ol>
        </section>
      </article>
    </main>
  );
}
