import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Manifest — Nie głosuj",
  description:
    "Dlaczego powstała ta strona i dlaczego warto znać programy partii przed oddaniem głosu.",
};

export default function ManifestPage() {
  return (
    <main className="app-shell page-shell">
      <Link href="/" className="back-link">
        ← Powrót do porównywarki
      </Link>

      <article className="card section-card page-content">
        <h1>Manifest</h1>

        <section className="manifest-section">
          <h2>Dlaczego powstała ta strona?</h2>
          <p>
            Żyjemy w czasach, gdy informacje polityczne docierają do nas głównie
            w postaci krótkich, emocjonalnych komunikatów — nagłówków, postów w
            mediach społecznościowych, krzykliwych sloganów wyborczych. Taki
            sposób komunikacji nie sprzyja podejmowaniu świadomych decyzji.
          </p>
          <p>
            <strong>„Nie głosuj — dopóki nie poznasz programu i faktów"</strong> to
            projekt stworzony po to, by pomóc obywatelom w podejmowaniu lepszych,
            bardziej świadomych decyzji wyborczych. Dostarczamy rzetelne,
            aktualne i obiektywne informacje o partiach politycznych — zarówno o tym,
            co deklarują w swoich oficjalnych programach, jak i o tym, jak ich posłowie
            naprawdę głosują w Sejmie.
          </p>
        </section>

        <section className="manifest-section">
          <h2>Jaki jest nasz cel?</h2>
          <ul className="manifest-list">
            <li>
              <strong>Świadome głosowanie.</strong> Chcemy, żeby każdy wyborca
              mógł porównać programy partii w tematach, które go interesują —
              zdrowie, podatki, edukacja, obronność — i na tej podstawie podjąć
              decyzję, zamiast kierować się sympatią do lidera czy przekazem
              medialnym.
            </li>
            <li>
              <strong>Transparentność.</strong> Udostępniamy bezpośrednie cytaty
              z oficjalnych programów partyjnych i linki do źródeł, tak by każdy
              mógł samodzielnie zweryfikować informacje.
            </li>
            <li>
              <strong>Weryfikacja obietnic przez czyny.</strong> Dzięki
              integracji z API Sejmu RP pokazujemy, jak poszczególne kluby
              parlamentarne naprawdę głosowały w kluczowych sprawach — bo
              programy to obietnice, a głosowania to fakty.
            </li>
            <li>
              <strong>Apolityczność narzędzia.</strong> Ten projekt nie
              promuje żadnej partii ani opcji politycznej. Algorytmy porównawcze
              traktują wszystkie partie równo, a odpowiedzi generowane są na
              podstawie treści dokumentów, nie naszych opinii.
            </li>
          </ul>
        </section>

        <section className="manifest-section">
          <h2>Dlaczego to ważne?</h2>
          <p>
            W Polsce frekwencja wyborcza rośnie, ale jednocześnie badania
            pokazują, że wielu wyborców nie zna szczegółów programów partii, na
            które głosują. To paradoks współczesnej demokracji — mamy dostęp do
            ogromnej ilości informacji, a jednocześnie coraz trudniej odróżnić
            fakty od propagandy.
          </p>
          <p>
            Wierzymy, że technologia — w tym sztuczna inteligencja — może pomóc
            w budowaniu bardziej świadomego społeczeństwa obywatelskiego. Nie
            zastępujemy krytycznego myślenia — dostarczamy narzędzia, które je
            wspierają.
          </p>
        </section>

        <section className="manifest-section">
          <h2>Jak działamy?</h2>
          <p>
            Analizujemy oficjalne dokumenty programowe partii politycznych,
            przetwarzamy je za pomocą technologii RAG (Retrieval-Augmented
            Generation) i udostępniamy w formie prostej porównywarki. Dodatkowo,
            korzystamy z publicznego{" "}
            <a
              href="https://api.sejm.gov.pl"
              target="_blank"
              rel="noreferrer"
            >
              API Sejmu RP
            </a>{" "}
            oraz{" "}
            <a
              href="https://api.sejm.gov.pl/eli"
              target="_blank"
              rel="noreferrer"
            >
              Europejskiego Identyfikatora Prawodawstwa (ELI)
            </a>
            , żeby prezentować wyniki rzeczywistych głosowań sejmowych.
          </p>
          <p>
            Wszystkie źródła danych są publiczne i jawne. Nie gromadzimy danych
            osobowych użytkowników poza dobrowolnym formularzem kontaktowym.
          </p>
        </section>

        <section className="manifest-section">
          <h2>Dołącz do nas</h2>
          <p>
            Jeśli podzielasz naszą misję i masz pomysły, jak ulepszyć to
            narzędzie — napisz do nas przez{" "}
            <Link href="/kontakt">formularz kontaktowy</Link>. Każda sugestia,
            każde zgłoszenie błędu i każda propozycja nowej funkcji jest dla nas
            cenna.
          </p>
        </section>
      </article>
    </main>
  );
}
