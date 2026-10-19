import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from logger import log_error, log_header, log_info, log_success
from src.backend.config import settings
from src.backend.parties import PARTY_CONFIGS, PartyKey, load_calculated_positions

load_dotenv()

POSITION_PROMPT = """Jesteś analitykiem politologicznym.
Na podstawie poniższego kontekstu z programu partii oszacuj pozycję partii na osiach:
- axis_x: gospodarka/społeczne od -1.0 (lewicowe) do 1.0 (prawicowe)
- axis_y: światopogląd od -1.0 (progresywne) do 1.0 (konserwatywne)

Wymagania:
1. Używaj wyłącznie informacji z kontekstu.
2. Nie zgaduj: jeśli dane są słabe, daj wynik bliżej 0.
3. axis_label to krótka etykieta po polsku (2-4 słowa), np. "centrowo-liberalna".
4. justification to jedno konkretne zdanie po polsku.
5. Odpowiedz WYŁĄCZNIE JSON-em:
{{"axis_x": number, "axis_y": number, "axis_label": string, "justification": string}}

Kontekst:
{context}
"""

AXIS_QUERIES = (
    "gospodarka podatki rynek praca świadczenia państwo socjalne",
    "światopogląd rodzina religia prawa kobiet prawa osób LGBT edukacja",
    "ustrój państwa wolności obywatelskie sądy media wartości",
)


def _resolve_source_url(metadata: dict[str, Any]) -> str:
    for key in ("source", "url"):
        value = metadata.get(key)
        if isinstance(value, str) and value:
            return value
    programme_url = metadata.get("programme_url")
    if isinstance(programme_url, str) and programme_url:
        return programme_url
    return "brak-źródła"


def _extract_json_object(text: str) -> dict[str, Any]:
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("Model response does not contain a JSON object.")
    return json.loads(text[start : end + 1])


def _clamp(value: float) -> float:
    return max(-1.0, min(1.0, value))


def _build_context(vector_store: Chroma) -> tuple[str, list[str]]:
    seen_fingerprints: set[str] = set()
    context_parts: list[str] = []
    used_sources: list[str] = []

    for query in AXIS_QUERIES:
        docs_with_scores = vector_store.similarity_search_with_score(
            query=query,
            k=settings.party_positioning_k,
        )
        for doc, _score in docs_with_scores:
            content = doc.page_content.strip()
            if not content:
                continue
            fingerprint = content[:240]
            if fingerprint in seen_fingerprints:
                continue
            seen_fingerprints.add(fingerprint)
            source_url = _resolve_source_url(doc.metadata)
            used_sources.append(source_url)
            context_parts.append(f"[{source_url}] {content[:900]}")

    return "\n\n".join(context_parts), sorted(set(used_sources))


def calculate_party_position(
    party_key: PartyKey,
    llm: ChatOpenAI,
    embeddings: OpenAIEmbeddings,
) -> dict[str, Any]:
    party = PARTY_CONFIGS[party_key]
    vector_store = Chroma(
        collection_name=party.index_name,
        embedding_function=embeddings,
        persist_directory=settings.chroma_persist_directory,
    )
    context, used_sources = _build_context(vector_store)
    if not context.strip():
        raise RuntimeError(
            f"Brak danych kontekstowych dla partii '{party.display_name}' "
            f"w kolekcji '{party.index_name}'."
        )

    response = llm.invoke(POSITION_PROMPT.format(context=context))
    payload = _extract_json_object(
        response.content if isinstance(response.content, str) else str(response.content)
    )

    axis_x = payload.get("axis_x")
    axis_y = payload.get("axis_y")
    axis_label = payload.get("axis_label")
    justification = payload.get("justification")

    if not isinstance(axis_x, (int, float)):
        raise ValueError(f"Model returned invalid axis_x for '{party_key}': {axis_x!r}")
    if not isinstance(axis_y, (int, float)):
        raise ValueError(f"Model returned invalid axis_y for '{party_key}': {axis_y!r}")
    if not isinstance(axis_label, str) or not axis_label.strip():
        raise ValueError(
            f"Model returned invalid axis_label for '{party_key}': {axis_label!r}"
        )
    if not isinstance(justification, str) or not justification.strip():
        raise ValueError(
            f"Model returned invalid justification for '{party_key}': {justification!r}"
        )

    return {
        "axis_x": round(_clamp(float(axis_x)), 3),
        "axis_y": round(_clamp(float(axis_y)), 3),
        "axis_label": axis_label.strip(),
        "justification": justification.strip(),
        "source_urls": used_sources,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Calculate political-chart positions from party programmes stored in Chroma."
    )
    parser.add_argument(
        "--party",
        choices=[*PARTY_CONFIGS.keys(), "all"],
        default="all",
        help="Calculate one party or all parties.",
    )
    parser.add_argument(
        "--output",
        default=settings.party_positions_path,
        help="Output JSON file path.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    selected: list[PartyKey]
    if args.party == "all":
        selected = list(PARTY_CONFIGS.keys())
    else:
        selected = [args.party]

    log_header("Calculating party chart positions")
    log_info(f"Using Chroma persist directory: {settings.chroma_persist_directory}")
    log_info(f"Output file: {args.output}")

    existing_positions = load_calculated_positions(args.output)
    calculated_parties: dict[str, Any] = {
        key: dict(value) for key, value in existing_positions.items()
    }

    llm = ChatOpenAI(model=settings.chat_model, temperature=0)
    embeddings = OpenAIEmbeddings(model=settings.embeddings_model)

    for party_key in selected:
        party = PARTY_CONFIGS[party_key]
        log_info(f"Calculating position for: {party.display_name}")
        calculated_parties[party_key] = calculate_party_position(
            party_key=party_key,
            llm=llm,
            embeddings=embeddings,
        )
        log_success(
            f"{party.display_name}: x={calculated_parties[party_key]['axis_x']}, "
            f"y={calculated_parties[party_key]['axis_y']} "
            f"({calculated_parties[party_key]['axis_label']})"
        )

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": settings.chat_model,
        "embeddings_model": settings.embeddings_model,
        "retrieval_k": settings.party_positioning_k,
        "parties": calculated_parties,
    }
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    log_success(f"Saved calculated positions to: {output_path}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        log_error(f"Position calculation failed: {exc}")
        raise
