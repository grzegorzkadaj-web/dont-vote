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

type DeputyListItem = {
  id: number;
  first_last_name: string;
  last_first_name: string;
  club: string;
  club_display_name: string;
  district_name: string | null;
  district_num: number | null;
  email: string | null;
  photo_url: string;
  active: boolean;
};

type DeputyActivityStats = {
  deputy_id: number;
  total_votings: number;
  voted_votings: number;
  unexcused_absences: number;
  unexcused_absence_days: number;
  excused_absences: number;
  attendance_rate: number;
  club_id: string;
  party_name: string;
  act_proposals_count: number;
  interpellations_count: number;
  written_questions_count: number;
  term: number;
};

type TavilySearchResultItem = {
  title: string;
  url: string;
  snippet: string;
  score: number | null;
};

type DeputyPublicInfo = {
  query: string;
  answer: string | null;
  sources: TavilySearchResultItem[];
};

type DeputyDossierResponse = {
  deputy: DeputyListItem;
  activity_stats: DeputyActivityStats;
  public_info: DeputyPublicInfo;
};

type PoliticianVotingDetail = {
  sitting: number;
  voting_number: number;
  short_title: string;
  category: string;
  axis: "x" | "y";
  vote: "YES" | "NO" | "ABSTAIN" | "ABSENT" | string;
  vote_label: string;
  impact: string;
  description: string;
};

type PoliticianPosition = {
  deputy_id: number;
  first_last_name: string;
  club: string;
  club_display_name: string;
  photo_url: string;
  axis_x: number;
  axis_y: number;
  axis_label: string;
  summary: string;
  economic_description: string;
  worldview_description: string;
  voting_details: PoliticianVotingDetail[];
  calculated_at: string;
};

type TabKey = "position" | "politicians" | "question" | "poll" | "votings" | "dossier";

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

  // Deputy dossier state
  const [deputies, setDeputies] = useState<DeputyListItem[]>([]);
  const [deputiesLoading, setDeputiesLoading] = useState(false);
  const [deputiesError, setDeputiesError] = useState<string | null>(null);
  const [deputySearchQuery, setDeputySearchQuery] = useState("");
  const [selectedClubFilter, setSelectedClubFilter] = useState<string>("ALL");
  const [selectedDeputyId, setSelectedDeputyId] = useState<number | null>(null);
  const [dossierLoading, setDossierLoading] = useState(false);
  const [dossierError, setDossierError] = useState<string | null>(null);
  const [dossierData, setDossierData] = useState<DeputyDossierResponse | null>(null);

  // Politician positions state
  const [politicians, setPoliticians] = useState<PoliticianPosition[]>([]);
  const [politiciansLoading, setPoliticiansLoading] = useState(false);
  const [politiciansError, setPoliticiansError] = useState<string | null>(null);
  const [selectedPoliticianIds, setSelectedPoliticianIds] = useState<number[]>([]);
  const [politicianSearchQuery, setPoliticianSearchQuery] = useState("");
  const [politicianClubFilter, setPoliticianClubFilter] = useState<string>("ALL");
  const [expandedVotingDetailsMpId, setExpandedVotingDetailsMpId] = useState<number | null>(null);

  const loadPoliticianPositions = async () => {
    if (politicians.length > 0 || politiciansLoading) return;
    setPoliticiansLoading(true);
    setPoliticiansError(null);
    try {
      const response = await fetch(buildApiUrl("/api/politicians/positions"));
      if (!response.ok) {
        throw new Error("Nie udało się pobrać pozycji polityków z bazy danych.");
      }
      const data = (await response.json()) as PoliticianPosition[];
      setPoliticians(data);
      // Domyślnie zaznacz kilku charakterystycznych liderów z różnych formacji
      const defaultLeaderNames = [
        "Donald Tusk",
        "Jarosław Kaczyński",
        "Krzysztof Bosak",
        "Adrian Zandberg",
        "Władysław Kosiniak-Kamysz",
        "Szymon Hołownia"
      ];
      const defaultIds = data
        .filter((p) => defaultLeaderNames.includes(p.first_last_name))
        .map((p) => p.deputy_id);
      setSelectedPoliticianIds(defaultIds.length > 0 ? defaultIds : data.slice(0, 5).map((p) => p.deputy_id));
    } catch (err) {
      setPoliticiansError(err instanceof Error ? err.message : "Błąd ładowania pozycji polityków.");
    } finally {
      setPoliticiansLoading(false);
    }
  };

  useEffect(() => {
    if (activeTab === "politicians") {
      void loadPoliticianPositions();
    }
  }, [activeTab]);

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

  const loadDeputiesList = async () => {
    if (deputies.length > 0 || deputiesLoading) return;
    setDeputiesLoading(true);
    setDeputiesError(null);
    try {
      const response = await fetch(buildApiUrl("/api/deputies"));
      if (!response.ok) {
        throw new Error("Nie udało się pobrać listy posłów z Sejmu RP.");
      }
      const data = (await response.json()) as DeputyListItem[];
      setDeputies(data);
    } catch (err) {
      setDeputiesError(err instanceof Error ? err.message : "Błąd podczas ładowania posłów.");
    } finally {
      setDeputiesLoading(false);
    }
  };

  const loadDeputyDossier = async (deputyId: number) => {
    setSelectedDeputyId(deputyId);
    setDossierLoading(true);
    setDossierError(null);
    try {
      const response = await fetch(buildApiUrl(`/api/deputies/${deputyId}/dossier`));
      if (!response.ok) {
        const details = await response.text();
        throw new Error(`Błąd pobierania dossier posła: ${details}`);
      }
      const data = (await response.json()) as DeputyDossierResponse;
      setDossierData(data);
    } catch (err) {
      setDossierError(err instanceof Error ? err.message : "Nieznany błąd podczas ładowania dossier posła.");
    } finally {
      setDossierLoading(false);
    }
  };

  useEffect(() => {
    if (activeTab === "dossier") {
      void loadDeputiesList();
    }
  }, [activeTab]);

  const uniqueClubs = useMemo(() => {
    const clubMap = new Map<string, string>();
    for (const d of deputies) {
      if (d.club && !clubMap.has(d.club)) {
        clubMap.set(d.club, d.club_display_name || d.club);
      }
    }
    return Array.from(clubMap.entries()).map(([club, displayName]) => ({
      club,
      displayName
    }));
  }, [deputies]);

  const filteredDeputies = useMemo(() => {
    const query = deputySearchQuery.trim().toLowerCase();
    return deputies.filter((d) => {
      const matchesClub = selectedClubFilter === "ALL" || d.club === selectedClubFilter;
      if (!matchesClub) return false;
      if (!query) return true;
      const fullName = d.first_last_name.toLowerCase();
      const clubName = (d.club_display_name || d.club).toLowerCase();
      const district = (d.district_name || "").toLowerCase();
      return (
        fullName.includes(query) ||
        clubName.includes(query) ||
        district.includes(query)
      );
    });
  }, [deputies, deputySearchQuery, selectedClubFilter]);

  const togglePoliticianSelection = (id: number) => {
    setSelectedPoliticianIds((prev) =>
      prev.includes(id) ? prev.filter((pId) => pId !== id) : [...prev, id]
    );
  };

  const selectAllFilteredPoliticians = () => {
    const idsToAdd = filteredPoliticians.map((p) => p.deputy_id);
    setSelectedPoliticianIds((prev) => Array.from(new Set([...prev, ...idsToAdd])));
  };

  const deselectAllPoliticians = () => {
    setSelectedPoliticianIds([]);
  };

  const uniquePoliticianClubs = useMemo(() => {
    const clubMap = new Map<string, string>();
    for (const p of politicians) {
      if (p.club && !clubMap.has(p.club)) {
        clubMap.set(p.club, p.club_display_name || p.club);
      }
    }
    return Array.from(clubMap.entries()).map(([club, displayName]) => ({
      club,
      displayName
    }));
  }, [politicians]);

  const filteredPoliticians = useMemo(() => {
    const query = politicianSearchQuery.trim().toLowerCase();
    return politicians.filter((p) => {
      const matchesClub = politicianClubFilter === "ALL" || p.club === politicianClubFilter;
      if (!matchesClub) return false;
      if (!query) return true;
      const fullName = p.first_last_name.toLowerCase();
      const clubName = (p.club_display_name || p.club).toLowerCase();
      const label = (p.axis_label || "").toLowerCase();
      return fullName.includes(query) || clubName.includes(query) || label.includes(query);
    });
  }, [politicians, politicianSearchQuery, politicianClubFilter]);

  const selectedPoliticiansList = useMemo(() => {
    const idSet = new Set(selectedPoliticianIds);
    return politicians.filter((p) => idSet.has(p.deputy_id));
  }, [politicians, selectedPoliticianIds]);

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
        <h2>Zadawaj pytania o programy, sprawdzaj rzeczywiste głosowania posłów w Sejmie i poznaj stanowiska partii zanim podejmiesz decyzję.</h2>
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
            aria-selected={activeTab === "politicians"}
            className={`tab-button ${activeTab === "politicians" ? "active" : ""}`}
            onClick={() => setActiveTab("politicians")}
          >
            Pozycja polityka na scenie politycznej
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
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === "dossier"}
            className={`tab-button ${activeTab === "dossier" ? "active" : ""}`}
            onClick={() => setActiveTab("dossier")}
          >
            Dossier parlamentarzysty
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

      {activeTab === "politicians" && (
        <section className="card section-card">
          <div className="section-header-block">
            <h2>Pozycja polityka na scenie politycznej</h2>
            <p className="muted">
              Wizualizacja rzeczywistych poglądów posłów na podstawie ich imiennych głosowań w Sejmie X kadencji.
              Wybierz posłów z poniższej listy za pomocą checkboxa, aby nanieść ich na mapę i porównać ich położenie.
            </p>
          </div>

          {politiciansError && (
            <div className="error-card" style={{ marginBottom: "16px" }}>
              <strong>Błąd:</strong> {politiciansError}
            </div>
          )}

          {/* Wykres dla wybranych polityków */}
          <div className="politician-map-wrapper">
            <p className="muted axis-legend">
              Oś X: poglądy gospodarczo-społeczne (lewicowe → wolnorynkowe). Oś Y: poglądy światopoglądowe
              (progresywne → konserwatywne).
            </p>
            <div className="party-map politician-map">
              <span className="axis-label axis-label-x-left">Lewica gospodarcza / socjalna</span>
              <span className="axis-label axis-label-x-right">Prawica gospodarcza / wolny rynek</span>
              <span className="axis-label axis-label-y-top">Konserwatyzm światopoglądowy</span>
              <span className="axis-label axis-label-y-bottom">Progresywność światopoglądowa</span>
              <div className="axis-x" />
              <div className="axis-y" />

              {/* Tło - orientacyjne kropki partii w tle */}
              {parties.map((party) => (
                <span
                  key={`bg-party-${party.key}`}
                  className="party-dot bg-party-dot"
                  style={{
                    left: `${(party.axis_x + 1) * 50}%`,
                    top: `${(1 - (party.axis_y + 1) * 0.5) * 100}%`
                  }}
                  title={`Partia: ${party.display_name}`}
                >
                  {party.display_name}
                </span>
              ))}

              {/* Kropki zaznaczonych posłów */}
              {selectedPoliticiansList.map((pol) => {
                const posX = (pol.axis_x + 1) * 50;
                const posY = (1 - (pol.axis_y + 1) * 0.5) * 100;
                return (
                  <div
                    key={`map-pol-${pol.deputy_id}`}
                    className="politician-dot"
                    style={{
                      left: `${posX}%`,
                      top: `${posY}%`
                    }}
                    title={`${pol.first_last_name} (${pol.club}) - ${pol.axis_label}\nX: ${pol.axis_x.toFixed(2)}, Y: ${pol.axis_y.toFixed(2)}`}
                  >
                    {pol.photo_url ? (
                      <img
                        src={pol.photo_url}
                        alt={pol.first_last_name}
                        className="politician-dot-avatar"
                        onError={(e) => {
                          (e.target as HTMLElement).style.display = "none";
                        }}
                      />
                    ) : (
                      <div className="politician-dot-fallback">{pol.first_last_name.slice(0, 2)}</div>
                    )}
                    <span className="politician-dot-name">{pol.first_last_name}</span>
                  </div>
                );
              })}

              {selectedPoliticiansList.length === 0 && !politiciansLoading && (
                <div className="map-empty-hint">
                  Zaznacz posłów na poniższej liście, aby zobaczyć ich pozycję na wykresie.
                </div>
              )}
            </div>
            <div className="chart-legend-row">
              <span className="legend-chip">
                Wybrani posłowie: <strong>{selectedPoliticiansList.length}</strong>
              </span>
              <span className="legend-chip muted-chip">
                W tle wyświetlane są referencyjne punkty głównych partii
              </span>
            </div>
          </div>

          {/* Pasek narzędzi i filtry listy */}
          <div className="politicians-toolbar">
            <div className="search-and-filter-row">
              <input
                type="text"
                placeholder="Szukaj posła po nazwisku, klubie..."
                value={politicianSearchQuery}
                onChange={(e) => setPoliticianSearchQuery(e.target.value)}
                className="dossier-search-input"
              />
              <select
                value={politicianClubFilter}
                onChange={(e) => setPoliticianClubFilter(e.target.value)}
                className="club-filter-select"
              >
                <option value="ALL">Wszystkie kluby i koła ({politicians.length})</option>
                {uniquePoliticianClubs.map(({ club, displayName }) => (
                  <option key={club} value={club}>
                    {club} — {displayName}
                  </option>
                ))}
              </select>
            </div>

            <div className="selection-actions-row">
              <button
                type="button"
                className="secondary btn-sm"
                onClick={selectAllFilteredPoliticians}
              >
                Zaznacz widocznych ({filteredPoliticians.length})
              </button>
              <button
                type="button"
                className="secondary btn-sm"
                onClick={deselectAllPoliticians}
                disabled={selectedPoliticianIds.length === 0}
              >
                Odznacz wszystkich
              </button>
              <span className="toolbar-counter">
                Pokazano {filteredPoliticians.length} z {politicians.length} posłów
              </span>
            </div>
          </div>

          {/* Lista polityków z checkboxem, opisem i szczegółami głosowań */}
          {politiciansLoading ? (
            <div className="loading-state">
              <div className="spinner" />
              <p>Ładowanie danych posłów i analizy głosowań...</p>
            </div>
          ) : (
            <div className="politicians-list">
              {filteredPoliticians.map((pol) => {
                const isSelected = selectedPoliticianIds.includes(pol.deputy_id);
                const isExpanded = expandedVotingDetailsMpId === pol.deputy_id;

                return (
                  <article
                    key={`pol-card-${pol.deputy_id}`}
                    className={`politician-card ${isSelected ? "politician-card-selected" : ""}`}
                  >
                    <div className="politician-card-header">
                      <label className="politician-checkbox-label" title="Zaznacz, aby dodać na wykres">
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => togglePoliticianSelection(pol.deputy_id)}
                          className="politician-checkbox"
                        />
                        <span className="checkbox-custom-ui" />
                      </label>

                      <div className="politician-avatar-wrap">
                        {pol.photo_url ? (
                          <img
                            src={pol.photo_url}
                            alt={pol.first_last_name}
                            className="politician-avatar"
                            onError={(e) => {
                              (e.target as HTMLElement).style.display = "none";
                            }}
                          />
                        ) : (
                          <div className="politician-avatar-fallback">
                            {pol.first_last_name.slice(0, 2)}
                          </div>
                        )}
                      </div>

                      <div className="politician-info">
                        <div className="politician-title-row">
                          <h3 className="politician-name">{pol.first_last_name}</h3>
                          <span className="politician-club-badge" title={pol.club_display_name}>
                            {pol.club}
                          </span>
                          <span className="politician-axis-badge">
                            {pol.axis_label}
                          </span>
                        </div>
                        <div className="politician-coords-row">
                          <span className="coord-chip">
                            Gospodarka (X): <strong>{pol.axis_x > 0 ? `+${pol.axis_x.toFixed(2)}` : pol.axis_x.toFixed(2)}</strong>
                          </span>
                          <span className="coord-chip">
                            Światopogląd (Y): <strong>{pol.axis_y > 0 ? `+${pol.axis_y.toFixed(2)}` : pol.axis_y.toFixed(2)}</strong>
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Dlaczego lewica / prawica - opis oceny oparty na głosowaniach */}
                    <div className="politician-justification">
                      <p className="politician-summary-text">{pol.summary}</p>
                      <div className="politician-axis-breakdown-box">
                        <div className="breakdown-item">
                          <span className="breakdown-title">Oś gospodarcza:</span>
                          <span className="breakdown-desc">{pol.economic_description}</span>
                        </div>
                        <div className="breakdown-item">
                          <span className="breakdown-title">Oś światopoglądowa:</span>
                          <span className="breakdown-desc">{pol.worldview_description}</span>
                        </div>
                      </div>
                    </div>

                    {/* Przycisk rozwijania szczegółów głosowań */}
                    <div className="politician-actions-footer">
                      <button
                        type="button"
                        className="toggle-voting-details-btn"
                        onClick={() =>
                          setExpandedVotingDetailsMpId(isExpanded ? null : pol.deputy_id)
                        }
                      >
                        {isExpanded ? "▲ Ukryj szczegóły głosowań w Sejmie" : "▼ Zobacz szczegóły głosowań w Sejmie (" + (pol.voting_details?.length || 0) + ")"}
                      </button>
                    </div>

                    {/* Tabela szczegółów głosowań posła z Sejm API */}
                    {isExpanded && pol.voting_details && (
                      <div className="politician-voting-details-drawer">
                        <h4 className="details-header">
                          Rzeczywiste imienne decyzje posła w głosowaniach Sejmu X kadencji:
                        </h4>
                        <div className="voting-details-grid">
                          {pol.voting_details.map((vd, idx) => {
                            let voteBadgeClass = "badge-absent";
                            let voteText = "Nieobecny";
                            if (vd.vote === "YES") {
                              voteBadgeClass = "badge-yes";
                              voteText = "ZA";
                            } else if (vd.vote === "NO") {
                              voteBadgeClass = "badge-no";
                              voteText = "PRZECIW";
                            } else if (vd.vote === "ABSTAIN") {
                              voteBadgeClass = "badge-abstain";
                              voteText = "WSTRZYMAŁ SIĘ";
                            }

                            return (
                              <div key={`vd-${idx}`} className="voting-detail-card">
                                <div className="detail-top">
                                  <span className="voting-tag category-tag">{vd.category}</span>
                                  <span className={`voting-vote-badge ${voteBadgeClass}`}>
                                    {voteText}
                                  </span>
                                </div>
                                <div className="voting-title">{vd.short_title}</div>
                                <div className="voting-desc muted">{vd.description}</div>
                                <div className="voting-impact">
                                  <strong>Wpływ na ocenę:</strong> {vd.impact}
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    )}
                  </article>
                );
              })}
            </div>
          )}
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

      {activeTab === "dossier" && (
        <section className="card section-card dossier-container">
          <div className="dossier-intro">
            <h2>Dossier parlamentarzysty</h2>
            <p className="muted">
              Sprawdź statystyki aktywności posłów w Sejmie X kadencji oraz niezależne publiczne informacje
              zebrane przez sztuczną inteligencję z sieci.
            </p>
          </div>

          <div className="dossier-layout">
            {/* Left sidebar: Deputies list */}
            <aside className="deputies-sidebar">
              <div className="deputies-filter-box">
                <input
                  type="text"
                  placeholder="Szukaj posła po nazwisku lub okręgu..."
                  value={deputySearchQuery}
                  onChange={(e) => setDeputySearchQuery(e.target.value)}
                  className="deputy-search-input"
                />

                <div className="deputies-club-filter">
                  <select
                    value={selectedClubFilter}
                    onChange={(e) => setSelectedClubFilter(e.target.value)}
                    className="deputy-club-select"
                  >
                    <option value="ALL">Wszystkie kluby i koła ({deputies.length})</option>
                    {uniqueClubs.map((clubItem) => (
                      <option key={clubItem.club} value={clubItem.club}>
                        {clubItem.club} – {clubItem.displayName}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="deputies-count-badge">
                  Posłowie: <strong>{filteredDeputies.length}</strong> / {deputies.length}
                </div>
              </div>

              {deputiesLoading && (
                <div className="deputies-loading-box">
                  <div className="loading-spinner" aria-hidden />
                  <p>Ładowanie listy posłów...</p>
                </div>
              )}

              {deputiesError && (
                <div className="error-card small">
                  <strong>Błąd:</strong> {deputiesError}
                </div>
              )}

              <div className="deputies-scroll-list" role="list">
                {filteredDeputies.map((deputy) => {
                  const isSelected = selectedDeputyId === deputy.id;
                  return (
                    <button
                      key={deputy.id}
                      type="button"
                      role="listitem"
                      onClick={() => void loadDeputyDossier(deputy.id)}
                      className={`deputy-item-btn ${isSelected ? "selected" : ""}`}
                    >
                      <img
                        src={deputy.photo_url}
                        alt={deputy.first_last_name}
                        className="deputy-avatar"
                        loading="lazy"
                        onError={(e) => {
                          (e.currentTarget as HTMLImageElement).style.visibility = "hidden";
                        }}
                      />
                      <div className="deputy-meta">
                        <div className="deputy-name">{deputy.first_last_name}</div>
                        <div className="deputy-sub-meta">
                          <span className="deputy-club-badge">{deputy.club}</span>
                          {deputy.district_name && (
                            <span className="deputy-district-text">
                              {deputy.district_name}
                            </span>
                          )}
                        </div>
                      </div>
                    </button>
                  );
                })}
                {!deputiesLoading && filteredDeputies.length === 0 && (
                  <div className="deputies-empty-text">Nie znaleziono posłów spełniających kryteria.</div>
                )}
              </div>
            </aside>

            {/* Right main panel: Dossier details */}
            <div className="deputy-detail-view">
              {!selectedDeputyId && !dossierLoading && (
                <div className="deputy-placeholder-box">
                  <div className="placeholder-icon">👤</div>
                  <h3>Wybierz parlamentarzystę z listy</h3>
                  <p className="muted">
                    Kliknij nazwisko posła po lewej stronie, aby wyświetlić pełne statystyki sejmowej aktywności
                    (głosowania, nieusprawiedliwione nieobecności, projekty ustaw) oraz zweryfikowane publiczne
                    informacje z sieci za pośrednictwem Tavily.
                  </p>
                </div>
              )}

              {dossierLoading && (
                <div className="deputy-detail-loading">
                  <div className="loading-spinner" aria-hidden />
                  <p>Generuję dossier parlamentarzysty (statystyki Sejmu + Tavily)...</p>
                </div>
              )}

              {dossierError && (
                <div className="card section-card error-card">
                  <strong>Błąd:</strong> {dossierError}
                </div>
              )}

              {dossierData && !dossierLoading && (
                <div className="deputy-dossier-content">
                  {/* Deputy header */}
                  <div className="deputy-profile-card">
                    <img
                      src={dossierData.deputy.photo_url}
                      alt={dossierData.deputy.first_last_name}
                      className="profile-avatar"
                      onError={(e) => {
                        (e.currentTarget as HTMLImageElement).style.visibility = "hidden";
                      }}
                    />
                    <div className="profile-info">
                      <h2>{dossierData.deputy.first_last_name}</h2>
                      <div className="profile-badges">
                        <span className="badge-club">
                          {dossierData.activity_stats.party_name} ({dossierData.activity_stats.club_id})
                        </span>
                        <span className="badge-term">Kadencja {dossierData.activity_stats.term}</span>
                        {dossierData.deputy.district_name && (
                          <span className="badge-district">
                            Okręg nr {dossierData.deputy.district_num} ({dossierData.deputy.district_name})
                          </span>
                        )}
                      </div>
                      {dossierData.deputy.email && (
                        <div className="profile-contact">
                          ✉️ <a href={`mailto:${dossierData.deputy.email}`}>{dossierData.deputy.email}</a>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Section 1: Sejm Activity Stats */}
                  <section className="dossier-section activity-section">
                    <div className="section-title-row">
                      <h3>📊 1. Statystyki aktywności poselskiej (API Sejmu RP)</h3>
                      <span className="source-tag">Oficjalne dane Sejmu</span>
                    </div>

                    <div className="stats-metric-grid">
                      <div className="stat-card">
                        <div className="stat-value">{dossierData.activity_stats.total_votings}</div>
                        <div className="stat-label">Liczba głosowań ogółem</div>
                        <div className="stat-subtext">
                          Wziął udział w: <strong>{dossierData.activity_stats.voted_votings}</strong> (
                          {dossierData.activity_stats.attendance_rate.toFixed(1)}%)
                        </div>
                      </div>

                      <div className="stat-card">
                        <div
                          className={`stat-value ${
                            dossierData.activity_stats.unexcused_absences > 0 ? "text-warn" : "text-good"
                          }`}
                        >
                          {dossierData.activity_stats.unexcused_absences}
                        </div>
                        <div className="stat-label">Nieusprawiedliwione nieobecności</div>
                        <div className="stat-subtext">
                          Dni opuszczone: <strong>{dossierData.activity_stats.unexcused_absence_days}</strong>
                          {dossierData.activity_stats.excused_absences > 0 &&
                            ` (usprawiedliwione: ${dossierData.activity_stats.excused_absences})`}
                        </div>
                      </div>

                      <div className="stat-card">
                        <div className="stat-value">{dossierData.activity_stats.club_id}</div>
                        <div className="stat-label">Przynależność klubowa</div>
                        <div className="stat-subtext">{dossierData.activity_stats.party_name}</div>
                      </div>

                      <div className="stat-card">
                        <div className="stat-value text-accent">
                          {dossierData.activity_stats.act_proposals_count}
                        </div>
                        <div className="stat-label">Poselskie projekty ustaw</div>
                        <div className="stat-subtext">Wnioski w X kadencji (inicjatywy poselskie)</div>
                      </div>
                    </div>

                    <div className="additional-activities-row">
                      <div className="activity-mini-pill">
                        📝 Interpelacje poselskie: <strong>{dossierData.activity_stats.interpellations_count}</strong>
                      </div>
                      <div className="activity-mini-pill">
                        ❓ Zapytania poselskie: <strong>{dossierData.activity_stats.written_questions_count}</strong>
                      </div>
                      <div className="activity-mini-pill">
                        🎯 Frekwencja w głosowaniach: <strong>{dossierData.activity_stats.attendance_rate.toFixed(1)}%</strong>
                      </div>
                    </div>
                  </section>

                  {/* Section 2: Other Public Information via Tavily */}
                  <section className="dossier-section public-info-section">
                    <div className="section-title-row">
                      <h3>🌐 2. Pozostałe informacje publiczne (Tavily AI Search)</h3>
                      <span className="source-tag">Wyszukiwanie otwartych źródeł</span>
                    </div>

                    {dossierData.public_info.answer ? (
                      <div className="tavily-answer-card">
                        <div className="answer-badge">Synteza AI ze źródeł publicznych</div>
                        <div className="answer-text">{dossierData.public_info.answer}</div>
                      </div>
                    ) : (
                      <div className="tavily-no-answer">
                        Brak wygenerowanego podsumowania tekstowego dla tej osoby. Poniżej znajdują się znalezione źródła.
                      </div>
                    )}

                    <div className="tavily-sources-container">
                      <h4>Znalezione materiały i artykuły w sieci:</h4>
                      {dossierData.public_info.sources.length === 0 ? (
                        <p className="muted">Nie odnaleziono bezpośrednich wpisów publicznych w usłudze Tavily.</p>
                      ) : (
                        <div className="tavily-sources-list">
                          {dossierData.public_info.sources.map((src, index) => (
                            <article key={`${src.url}-${index}`} className="tavily-source-card">
                              <div className="source-card-header">
                                <a
                                  href={src.url}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="source-title-link"
                                >
                                  {src.title || src.url}
                                </a>
                                {src.score !== null && src.score !== undefined && (
                                  <span className="source-score">trafność: {src.score.toFixed(2)}</span>
                                )}
                              </div>
                              <p className="source-snippet">{src.snippet}</p>
                              <div className="source-domain">
                                <a href={src.url} target="_blank" rel="noreferrer">
                                  {src.url}
                                </a>
                              </div>
                            </article>
                          ))}
                        </div>
                      )}
                    </div>
                  </section>
                </div>
              )}
            </div>
          </div>
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
