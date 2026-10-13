"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

type PartyOverview = {
  key: string;
  display_name: string;
  index_name: string;
  programme_url: string;
  axis_x: number;
  axis_y: number;
  axis_label: string;
};

type SourceItem = {
  url: string;
  score: number;
  snippet: string;
};

type PartyAnswer = {
  party_key: string;
  party_display_name: string;
  answer: string;
  sources: SourceItem[];
};

type AskResponse = {
  question: string;
  answers: PartyAnswer[];
};

const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000";

const buildApiUrl = (path: string): string =>
  `${backendUrl.replace(/\/+$/, "")}/${path.replace(/^\/+/, "")}`;

export default function HomePage() {
  const [question, setQuestion] = useState("Co partie mówią o ochronie zdrowia?");
  const [parties, setParties] = useState<PartyOverview[]>([]);
  const [selectedParties, setSelectedParties] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AskResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [feedbackState, setFeedbackState] = useState<Record<string, "saved" | undefined>>({});

  useEffect(() => {
    void fetch(buildApiUrl("/api/parties"))
      .then((res) => {
        if (!res.ok) {
          throw new Error("Nie udało się pobrać listy partii.");
        }
        return res.json() as Promise<PartyOverview[]>;
      })
      .then((data) => {
        setParties(data);
        setSelectedParties(data.map((party) => party.key));
      })
      .catch((fetchError: Error) => {
        setError(fetchError.message);
      });
  }, []);

  const canSubmit = useMemo(
    () => question.trim().length >= 5 && selectedParties.length > 0 && !loading,
    [loading, question, selectedParties.length]
  );

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setFeedbackState({});

    try {
      const response = await fetch(buildApiUrl("/api/ask"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: question.trim(),
          parties: selectedParties
        })
      });

      if (!response.ok) {
        const details = await response.text();
        throw new Error(`Zapytanie nie powiodło się: ${details}`);
      }

      const data = (await response.json()) as AskResponse;
      setResult(data);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Nieznany błąd.");
    } finally {
      setLoading(false);
    }
  };

  const toggleParty = (partyKey: string) => {
    setSelectedParties((previous) =>
      previous.includes(partyKey)
        ? previous.filter((value) => value !== partyKey)
        : [...previous, partyKey]
    );
  };

  const sendFeedback = async (partyKey: string, helpful: boolean) => {
    await fetch(buildApiUrl("/api/feedback"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question,
        party_key: partyKey,
        helpful
      })
    });
    setFeedbackState((previous) => ({ ...previous, [partyKey]: "saved" }));
  };

  return (
    <main className="app-shell">
      <header className="card hero">
        <div className="brand">
          <div className="brand-mark" aria-hidden>
            NG
          </div>
          <div>
            <p className="brand-name">Nie głosuj</p>
            <p className="brand-tagline">Dopóki nie poznasz programu</p>
          </div>
        </div>
        <h1>Porównywarka programów partii</h1>
        <p className="muted hero-copy">
          Zadawaj pytania o programy, porównuj stanowiska i sprawdzaj źródła zanim podejmiesz
          decyzję.
        </p>
      </header>

      <section className="card section-card">
        <form onSubmit={onSubmit} className="grid">
          <label>
            <strong>Pytanie do programów partii</strong>
            <textarea value={question} onChange={(event) => setQuestion(event.target.value)} />
          </label>

          <div className="grid grid-2 party-selector">
            {parties.map((party) => (
              <label key={party.key} className="party-option">
                <input
                  type="checkbox"
                  checked={selectedParties.includes(party.key)}
                  onChange={() => toggleParty(party.key)}
                />
                <span>{party.display_name}</span>
              </label>
            ))}
          </div>

          <div>
            <button type="submit" disabled={!canSubmit} className="primary">
              {loading ? "Analizuję..." : "Zapytaj"}
            </button>
          </div>
        </form>
      </section>

      <section className="card section-card">
        <h2>Pozycja partii (lewo ↔ prawo)</h2>
        <div className="party-map">
          <div className="axis-x" />
          <div className="axis-y" />
          {parties.map((party) => (
            <span
              key={party.key}
              className="party-dot"
              style={{
                left: `${(party.axis_x + 1) * 50}%`,
                top: `${(1 - (party.axis_y + 1) * 0.5) * 100}%`
              }}
              title={party.axis_label}
            >
              {party.display_name}
            </span>
          ))}
        </div>
      </section>

      {error && (
        <section className="card section-card error-card">
          <strong>Błąd:</strong> {error}
        </section>
      )}

      {result && (
        <section className="card section-card">
          <h2>Odpowiedzi</h2>
          <p className="muted">{result.question}</p>
          <div className="grid">
            {result.answers.map((answer) => (
              <article key={answer.party_key} className="card answer-card">
                <h3>{answer.party_display_name}</h3>
                <p>{answer.answer}</p>

                <strong>Źródła</strong>
                <ul className="sources">
                  {answer.sources.map((source) => (
                    <li key={`${answer.party_key}-${source.url}-${source.score}`}>
                      <a href={source.url} target="_blank" rel="noreferrer">
                        {source.url}
                      </a>{" "}
                      (score: {source.score.toFixed(3)})
                    </li>
                  ))}
                </ul>

                <div className="feedback-row">
                  <span>Czy odpowiedź była pomocna?</span>
                  <button
                    type="button"
                    className="secondary"
                    onClick={() => sendFeedback(answer.party_key, true)}
                  >
                    Tak
                  </button>
                  <button
                    type="button"
                    className="secondary"
                    onClick={() => sendFeedback(answer.party_key, false)}
                  >
                    Nie
                  </button>
                  {feedbackState[answer.party_key] === "saved" && <span>Zapisano</span>}
                </div>
              </article>
            ))}
          </div>
        </section>
      )}
    </main>
  );
}
