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
  axis_justification: string | null;
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

type PollAxis = "x" | "y";

type PollQuestion = {
  id: string;
  text: string;
  axis: PollAxis;
  weight: number;
  polarity: 1 | -1;
};

type PollOption = {
  value: number;
  label: string;
};

type VotingPartyStat = {
  club_id: string;
  club_name: string;
  yes: number;
  no: number;
  abstain: number;
  absent: number;
  total: number;
  stance: string;
  percent_yes: number;
  percent_no: number;
  percent_abstain: number;
};

type VotingTotalVotes = {
  yes: number;
  no: number;
  abstain: number;
  absent: number;
  total: number;
};

type ActVotingItem = {
  id: string;
  act_name: string;
  short_description: string;
  document_type: string;
  sitting: number;
  voting_number: number;
  date: string | null;
  topic: string | null;
  passed: boolean;
  display_address: string | null;
  eli: string | null;
  links: Record<string, string>;
  total_votes: VotingTotalVotes;
  parties: VotingPartyStat[];
};

type VotingsSearchResponse = {
  query: string;
  results_count: number;
  acts: ActVotingItem[];
};

type TabKey = "position" | "question" | "poll" | "votings";

const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000";

const buildApiUrl = (path: string): string =>
  `${backendUrl.replace(/\/+$/, "")}/${path.replace(/^\/+/, "")}`;

const clampAxisValue = (value: number): number => Math.max(-1, Math.min(1, value));

const pollQuestions: PollQuestion[] = [
  {
    id: "social-spending",
    text: "Państwo powinno zwiększać wydatki socjalne, nawet jeśli oznacza to wyższe podatki.",
    axis: "x",
    weight: 1,
    polarity: -1
  },
  {
    id: "free-market",
    text: "Wolny rynek i niższe podatki są ważniejsze niż rozbudowane usługi publiczne.",
    axis: "x",
    weight: 1,
    polarity: 1
  },
  {
    id: "workers-rights",
    text: "Państwo powinno mocniej regulować rynek pracy i wzmacniać prawa pracowników.",
    axis: "x",
    weight: 1,
    polarity: -1
  },
  {
    id: "tradition",
    text: "Tradycyjne wartości rodzinne powinny mieć pierwszeństwo w polityce publicznej.",
    axis: "y",
    weight: 1,
    polarity: 1
  },
  {
    id: "liberal-rights",
    text: "Państwo powinno rozszerzać prawa obyczajowe (np. związki partnerskie, dostęp do aborcji).",
    axis: "y",
    weight: 1,
    polarity: -1
  },
  {
    id: "religion",
    text: "Religia powinna odgrywać ważną rolę w decyzjach władz publicznych.",
    axis: "y",
    weight: 1,
    polarity: 1
  }
];

const pollOptions: PollOption[] = [
  { value: -2, label: "Zdecydowanie się nie zgadzam" },
  { value: -1, label: "Raczej się nie zgadzam" },
  { value: 0, label: "Neutralnie" },
  { value: 1, label: "Raczej się zgadzam" },
  { value: 2, label: "Zdecydowanie się zgadzam" }
];

const sampleVotingTopics = [
  "Zdrowie",
  "Podatki",
  "Renta wdowia",
  "In vitro",
  "Ceny energii",
  "Kredyt mieszkaniowy",
  "Wakacje od ZUS",
  "Edukacja",
  "Obronność"
];

export default function HomePage() {
  const [question, setQuestion] = useState("Co partie mówią o ochronie zdrowia?");
  const [parties, setParties] = useState<PartyOverview[]>([]);
  const [selectedParties, setSelectedParties] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AskResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [feedbackState, setFeedbackState] = useState<Record<string, "saved" | undefined>>({});
  const [pollAnswers, setPollAnswers] = useState<Record<string, number>>({});
  const [activeTab, setActiveTab] = useState<TabKey>("position");

  // Votings state
  const [votingSubject, setVotingSubject] = useState("");
  const [votingLoading, setVotingLoading] = useState(false);
  const [votingResult, setVotingResult] = useState<VotingsSearchResponse | null>(null);
  const [votingError, setVotingError] = useState<string | null>(null);

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

  const pollPosition = useMemo(() => {
    if (Object.keys(pollAnswers).length !== pollQuestions.length) {
      return null;
    }

    let sumX = 0;
    let sumY = 0;
    let weightX = 0;
    let weightY = 0;

    for (const questionItem of pollQuestions) {
      const answer = pollAnswers[questionItem.id];
      if (typeof answer !== "number") {
        return null;
      }
      const normalizedAnswer = answer / 2;
      const weightedContribution =
        normalizedAnswer * questionItem.weight * questionItem.polarity;
      if (questionItem.axis === "x") {
        sumX += weightedContribution;
        weightX += questionItem.weight;
      } else {
        sumY += weightedContribution;
        weightY += questionItem.weight;
      }
    }

    return {
      axis_x: clampAxisValue(weightX > 0 ? sumX / weightX : 0),
      axis_y: clampAxisValue(weightY > 0 ? sumY / weightY : 0)
    };
  }, [pollAnswers]);

  const pollMatches = useMemo(() => {
    if (!pollPosition) {
      return [];
    }

    const maxDistance = Math.sqrt(8);
    return [...parties]
      .map((party) => {
        const distance = Math.hypot(
          pollPosition.axis_x - party.axis_x,
          pollPosition.axis_y - party.axis_y
        );
        const similarity = Math.max(0, 1 - distance / maxDistance);
        return {
          ...party,
          similarity
        };
      })
      .sort((a, b) => b.similarity - a.similarity)
      .slice(0, 3);
  }, [parties, pollPosition]);

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

  const onPollAnswerChange = (questionId: string, value: number) => {
    setPollAnswers((previous) => ({ ...previous, [questionId]: value }));
  };

  const runVotingSearch = async (subjectToSearch: string) => {
    const trimmed = subjectToSearch.trim();
    if (trimmed.length < 2) return;

    setVotingSubject(trimmed);
    setVotingLoading(true);
    setVotingError(null);

    try {
      const response = await fetch(buildApiUrl("/api/votings/search"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: trimmed,
          limit: 8
        })
      });

      if (!response.ok) {
        const details = await response.text();
        throw new Error(`Błąd wyszukiwania: ${details}`);
      }

      const data = (await response.json()) as VotingsSearchResponse;
      setVotingResult(data);
    } catch (err) {
      setVotingError(err instanceof Error ? err.message : "Nieznany błąd podczas pobierania głosowań.");
    } finally {
      setVotingLoading(false);
    }
  };

  const onVotingSubmit = async (event: FormEvent) => {
    event.preventDefault();
    await runVotingSearch(votingSubject);
  };

  const politicalSceneChart = (
    <>
      <p className="muted axis-legend">
        Oś X: poglądy gospodarczo-społeczne (lewicowe → prawicowe). Oś Y: poglądy światopoglądowe
        (progresywne → konserwatywne).
      </p>
      <div className="party-map">
        <span className="axis-label axis-label-x-left">Lewica gospodarcza</span>
        <span className="axis-label axis-label-x-right">Prawica gospodarcza</span>
        <span className="axis-label axis-label-y-top">Konserwatyzm światopoglądowy</span>
        <span className="axis-label axis-label-y-bottom">Progresywność światopoglądowa</span>
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
        {pollPosition && (
          <span
            className="party-dot user-dot"
            style={{
              left: `${(pollPosition.axis_x + 1) * 50}%`,
              top: `${(1 - (pollPosition.axis_y + 1) * 0.5) * 100}%`
            }}
            title="Twoja pozycja z ankiety"
          >
            Ty
          </span>
        )}
      </div>
    </>
  );

  return (
    <main className="app-shell">
      <header className="card hero">
        <div className="brand">
          <div className="brand-mark" aria-hidden>
            NG
          </div>
          <div>
            <p className="brand-name">Nie głosuj</p>
            <p className="brand-tagline">Dopóki nie poznasz programu i głosowań</p>
          </div>
        </div>
        <h1>Porównywarka partii i głosowań Sejmu</h1>
        <p className="muted hero-copy">
          Zadawaj pytania o programy, sprawdzaj rzeczywiste głosowania posłów w Sejmie i poznaj
          stanowiska partii zanim podejmiesz decyzję.
        </p>
      </header>

      <section className="card section-card tabs-card">
        <div className="tabs-nav" role="tablist" aria-label="Nawigacja sekcji">
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === "position"}
            className={`tab-button ${activeTab === "position" ? "active" : ""}`}
            onClick={() => setActiveTab("position")}
          >
            Pozycja partii na scenie politycznej
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === "question"}
            className={`tab-button ${activeTab === "question" ? "active" : ""}`}
            onClick={() => setActiveTab("question")}
          >
            Pytanie do programów partii
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === "poll"}
            className={`tab-button ${activeTab === "poll" ? "active" : ""}`}
            onClick={() => setActiveTab("poll")}
          >
            Ankieta poglądów
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === "votings"}
            className={`tab-button ${activeTab === "votings" ? "active" : ""}`}
            onClick={() => setActiveTab("votings")}
          >
            Głosowania
          </button>
        </div>
      </section>

      {activeTab === "position" && (
        <section className="card section-card">
          <h2>Pozycja partii na scenie politycznej</h2>
          {politicalSceneChart}
          <div className="position-justifications">
            {parties.map((party) => (
              <article key={`justification-${party.key}`} className="justification-item">
                <h3>{party.display_name}</h3>
                <p className="muted">
                  <strong>{party.axis_label}:</strong>{" "}
                  {party.axis_justification ?? "Uzasadnienie pozycji nie jest jeszcze dostępne."}
                </p>
              </article>
            ))}
          </div>
        </section>
      )}

      {activeTab === "question" && (
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
      )}

      {activeTab === "poll" && (
        <section className="card section-card">
          <h2>Ankieta poglądów</h2>
          <p className="muted">
            Odpowiedz na kilka pytań, a obliczymy Twoją pozycję na osi politycznej i porównamy ją z
            partiami.
          </p>
          <div className="poll-grid">
            {pollQuestions.map((questionItem, index) => (
              <fieldset key={questionItem.id} className="poll-question">
                <legend>
                  {index + 1}. {questionItem.text}
                </legend>
                <div className="poll-options">
                  {pollOptions.map((option) => (
                    <label key={`${questionItem.id}-${option.value}`} className="poll-option">
                      <input
                        type="radio"
                        name={questionItem.id}
                        checked={pollAnswers[questionItem.id] === option.value}
                        onChange={() => onPollAnswerChange(questionItem.id, option.value)}
                      />
                      <span>{option.label}</span>
                    </label>
                  ))}
                </div>
              </fieldset>
            ))}
          </div>

          {pollPosition ? (
            <div className="poll-summary">
              <p>
                <strong>Twoja pozycja:</strong> X={pollPosition.axis_x.toFixed(2)}, Y=
                {pollPosition.axis_y.toFixed(2)}
              </p>
              <p className="muted">
                Najbliżej Ci do:{" "}
                {pollMatches.map((party, index) => (
                  <span key={party.key}>
                    {index > 0 ? ", " : ""}
                    {party.display_name} ({Math.round(party.similarity * 100)}%)
                  </span>
                ))}
                .
              </p>
            </div>
          ) : (
            <p className="muted">Wypełnij wszystkie pytania, aby zobaczyć wynik.</p>
          )}

          <div className="poll-chart-block">
            <h3>Scena polityczna i Twoja pozycja</h3>
            {politicalSceneChart}
          </div>
        </section>
      )}

      {activeTab === "votings" && (
        <section className="card section-card">
          <h2>Głosowania w Sejmie</h2>
          <p className="muted">
            Wpisz interesujący Cię temat lub sprawę (np. zdrowie, podatki, renta wdowia, in vitro,
            ceny energii, wakacje od ZUS), aby zobaczyć powiązane ustawy i sprawdzić, jak
            głosowały poszczególne partie. Dane pobierane są bezpośrednio z oficjalnego API Sejmu RP
            i Europejskiego Identyfikatora Prawa (ELI).
          </p>

          <form onSubmit={onVotingSubmit} className="votings-search-form">
            <div className="search-input-wrapper">
              <input
                type="text"
                className="search-input"
                placeholder="Czym się interesujesz? (np. ochrona zdrowia, podatki, in vitro, renta wdowia)..."
                value={votingSubject}
                onChange={(e) => setVotingSubject(e.target.value)}
              />
              <button
                type="submit"
                disabled={votingLoading || votingSubject.trim().length < 2}
                className="primary search-btn"
              >
                {votingLoading ? "Szukam..." : "Szukaj"}
              </button>
            </div>

            <div className="topic-suggestions">
              <span className="suggestions-label">Przykładowe tematy:</span>
              <div className="topic-pills-list">
                {sampleVotingTopics.map((topic) => (
                  <button
                    key={topic}
                    type="button"
                    className="topic-pill"
                    onClick={() => runVotingSearch(topic)}
                  >
                    {topic}
                  </button>
                ))}
              </div>
            </div>
          </form>

          {votingLoading && (
            <div className="votings-loading-box">
              <div className="loading-spinner" aria-hidden />
              <p>Pobieram ustawy i statystyki głosowań z API Sejmu RP...</p>
            </div>
          )}

          {votingError && (
            <div className="card section-card error-card">
              <strong>Błąd:</strong> {votingError}
            </div>
          )}

          {votingResult && !votingLoading && (
            <div className="voting-results-container">
              <div className="results-header">
                <h3>
                  Znaleziono {votingResult.results_count}{" "}
                  {votingResult.results_count === 1
                    ? "ustawę"
                    : votingResult.results_count > 1 && votingResult.results_count < 5
                    ? "ustawy"
                    : "ustaw"}{" "}
                  dla tematu „{votingResult.query}”
                </h3>
              </div>

              {votingResult.acts.length === 0 ? (
                <div className="empty-results-box">
                  <p>Nie znaleziono ustaw powiązanych z tym zapytaniem w obecnej kadencji Sejmu.</p>
                  <p className="muted">
                    Spróbuj wpisać inne hasło lub kliknij jeden z przykładowych tematów powyżej.
                  </p>
                </div>
              ) : (
                <div className="acts-list">
                  {votingResult.acts.map((act) => (
                    <article key={act.id} className="act-card">
                      <header className="act-header">
                        <div className="act-title-row">
                          <h4 className="act-title">{act.act_name}</h4>
                          <span
                            className={`status-badge ${
                              act.passed ? "badge-passed" : "badge-rejected"
                            }`}
                          >
                            {act.passed ? "✓ Uchwalona" : "✗ Odrzucona / w toku"}
                          </span>
                        </div>

                        <div className="act-metadata">
                          {act.date && (
                            <span className="meta-tag">
                              📅 {new Date(act.date).toLocaleDateString("pl-PL")}
                            </span>
                          )}
                          <span className="meta-tag">
                            Posiedzenie {act.sitting}, głosowanie {act.voting_number}
                          </span>
                          {act.display_address && (
                            <span className="meta-tag meta-published">
                              📜 {act.display_address}
                            </span>
                          )}
                          <span className="meta-tag meta-type">{act.document_type}</span>
                        </div>
                      </header>

                      <div className="act-desc-box">
                        <div className="act-desc-title">Krótki opis ustawy:</div>
                        <p className="act-desc-text">{act.short_description}</p>
                      </div>

                      <div className="total-votes-summary">
                        <span className="summary-label">Wynik głosowania w Sejmie:</span>
                        <div className="summary-stats-pills">
                          <span className="stat-pill stat-pill-yes">
                            Za: <strong>{act.total_votes.yes}</strong>
                          </span>
                          <span className="stat-pill stat-pill-no">
                            Przeciw: <strong>{act.total_votes.no}</strong>
                          </span>
                          <span className="stat-pill stat-pill-abstain">
                            Wstrzymało się: <strong>{act.total_votes.abstain}</strong>
                          </span>
                          <span className="stat-pill stat-pill-total">
                            Frekwencja:{" "}
                            <strong>
                              {act.total_votes.total > 0
                                ? Math.round(
                                    ((act.total_votes.yes +
                                      act.total_votes.no +
                                      act.total_votes.abstain) /
                                      act.total_votes.total) *
                                      100
                                  )
                                : 0}
                              %
                            </strong>
                          </span>
                        </div>
                      </div>

                      <div className="parties-voting-section">
                        <h5>Jak głosowały poszczególne partie:</h5>
                        <div className="parties-grid">
                          {act.parties.map((party) => {
                            const stanceClass =
                              party.stance === "ZA"
                                ? "stance-pill-yes"
                                : party.stance === "PRZECIW"
                                ? "stance-pill-no"
                                : party.stance === "WSTRZYMAŁ SIĘ"
                                ? "stance-pill-abstain"
                                : party.stance === "NIEOBECNI"
                                ? "stance-pill-absent"
                                : "stance-pill-split";

                            return (
                              <div key={party.club_id} className="party-vote-card">
                                <div className="party-card-top">
                                  <span className="party-name" title={party.club_name}>
                                    {party.club_name}
                                  </span>
                                  <span className={`stance-pill ${stanceClass}`}>
                                    {party.stance}
                                  </span>
                                </div>

                                <div
                                  className="stacked-progress-bar"
                                  title={`Za: ${party.yes} (${party.percent_yes}%), Przeciw: ${party.no} (${party.percent_no}%), Wstrzymało się: ${party.abstain} (${party.percent_abstain}%)`}
                                >
                                  <div
                                    className="bar-seg bar-seg-yes"
                                    style={{ width: `${party.percent_yes}%` }}
                                  />
                                  <div
                                    className="bar-seg bar-seg-no"
                                    style={{ width: `${party.percent_no}%` }}
                                  />
                                  <div
                                    className="bar-seg bar-seg-abstain"
                                    style={{ width: `${party.percent_abstain}%` }}
                                  />
                                </div>

                                <div className="party-numbers-row">
                                  <span className="num-item num-yes">{party.yes} za</span>
                                  <span className="num-item num-no">{party.no} przeciw</span>
                                  {party.abstain > 0 && (
                                    <span className="num-item num-abstain">
                                      {party.abstain} wstrz.
                                    </span>
                                  )}
                                  {party.absent > 0 && (
                                    <span className="num-item num-absent">
                                      {party.absent} nieob.
                                    </span>
                                  )}
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>

                      {Object.keys(act.links).length > 0 && (
                        <div className="act-links-row">
                          <span className="act-links-label">Źródła oficjalne:</span>
                          <div className="links-group">
                            {act.links.sejm_voting_pdf && (
                              <a
                                href={act.links.sejm_voting_pdf}
                                target="_blank"
                                rel="noreferrer"
                                className="act-link-pill"
                              >
                                📄 Wyniki głosowania Sejmu (PDF)
                              </a>
                            )}
                            {act.links.isap && (
                              <a
                                href={act.links.isap}
                                target="_blank"
                                rel="noreferrer"
                                className="act-link-pill"
                              >
                                🌐 Dokument w ISAP
                              </a>
                            )}
                            {act.links.eli && (
                              <a
                                href={act.links.eli}
                                target="_blank"
                                rel="noreferrer"
                                className="act-link-pill"
                              >
                                🇪🇺 Europejski Identyfikator Prawa (ELI)
                              </a>
                            )}
                          </div>
                        </div>
                      )}
                    </article>
                  ))}
                </div>
              )}
            </div>
          )}
        </section>
      )}

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
