import argparse
import json
import logging
from datetime import datetime, timezone
from typing import Any

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from logger import log_error, log_header, log_info, log_success
from src.backend.benchmark_votings import BENCHMARK_VOTINGS, BenchmarkVoting
from src.backend.config import settings
from src.backend.database import get_all_politician_positions, save_politician_positions
from src.backend.votings import SejmVotingService

load_dotenv()
logger = logging.getLogger(__name__)

POLITICIAN_ANALYSIS_PROMPT = """Jesteś analitykiem politologicznym i ekspertem ds. zachowań parlamentarnych w Sejmie RP.
Przeanalizuj rzeczywiste wyniki głosowań posła/posłanki w Sejmie X kadencji.

Poseł/Posłanka: {name}
Klub/Koło: {club_display_name} ({club})
Obliczone współrzędne na osiach:
- Oś X (gospodarczo-społeczna: od -1.0 [lewica społeczno-gospodarcza / państwo opiekuńcze] do 1.0 [prawica wolnorynkowa / niskie podatki]): {axis_x}
- Oś Y (światopoglądowa: od -1.0 [progresywność / prawa kobiet i mniejszości] do 1.0 [konserwatyzm / tradycyjne wartości]): {axis_y}

Zestawienie kluczowych głosowań posła:
{votings_summary}

Twoje zadanie:
1. Przygotuj syntetyczne, obiektywne podsumowanie ("summary") – 1-2 zdania tłumaczące, co czyni tego posła lewicowym, prawicowym, liberalnym bądź konserwatywnym na podstawie jego realnych głosowań.
2. Krótki opis profilu gospodarczego ("economic_description") – 1 zdanie o podejściu do podatków, wydatków socjalnych i regulacji.
3. Krótki opis profilu światopoglądowego ("worldview_description") – 1 zdanie o podejściu do spraw bioetycznych, obyczajowych i praw mniejszości.

Zwróć WYŁĄCZNIE poprawny format JSON (bez bloków markdown ```json):
{{
  "summary": "...",
  "economic_description": "...",
  "worldview_description": "..."
}}
"""


def _clamp(val: float) -> float:
    return max(-1.0, min(1.0, val))


def _extract_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError(f"Brak obiektu JSON w odpowiedzi: {text}")
    return json.loads(text[start : end + 1])


def derive_axis_label(axis_x: float, axis_y: float) -> str:
    """Określa słowną etykietę pozycji w oparciu o kwadranty sceny politycznej."""
    # X: < -0.2 lewica, -0.2..0.2 centrum, > 0.2 prawica
    # Y: < -0.2 progresywna, -0.2..0.2 umiarkowana, > 0.2 konserwatywna
    if axis_x < -0.2 and axis_y < -0.2:
        return "lewicowo-progresywna"
    elif axis_x < -0.2 and axis_y > 0.2:
        return "lewicowo-konserwatywna"
    elif axis_x < -0.2:
        return "socjalno-centrowa"
    elif axis_x > 0.2 and axis_y > 0.2:
        return "prawicowo-konserwatywna"
    elif axis_x > 0.2 and axis_y < -0.2:
        return "prawicowo-liberalna"
    elif axis_x > 0.2:
        return "wolnorynkowa"
    elif axis_y < -0.2:
        return "centrowo-progresywna"
    elif axis_y > 0.2:
        return "centrowo-konserwatywna"
    else:
        return "umiarkowane centrum"


def fetch_all_benchmark_votes(
    voting_svc: SejmVotingService,
) -> dict[tuple[int, int], dict[int, str]]:
    """Pobiera głosy wszystkich posłów dla każdego z 10 kluczowych głosowań."""
    benchmark_data: dict[tuple[int, int], dict[int, str]] = {}
    for bv in BENCHMARK_VOTINGS:
        log_info(f"Pobieram głosowanie {bv.sitting}/{bv.voting_number}: {bv.short_title}")
        details = voting_svc.get_voting_details(bv.sitting, bv.voting_number)
        mp_votes: dict[int, str] = {}
        for vote_item in details.get("votes", []):
            mp_id = vote_item.get("MP")
            vote_val = vote_item.get("vote", "ABSENT")
            if mp_id:
                mp_votes[mp_id] = vote_val
        benchmark_data[(bv.sitting, bv.voting_number)] = mp_votes
    return benchmark_data


def compute_mp_raw_position(
    mp_id: int,
    benchmark_data: dict[tuple[int, int], dict[int, str]],
) -> tuple[float, float, list[dict[str, Any]]]:
    """Oblicza wartości numeryczne axis_x i axis_y oraz szczegóły głosowań dla posła."""
    x_contributions: list[float] = []
    y_contributions: list[float] = []
    voting_details: list[dict[str, Any]] = []

    vote_translations = {
        "YES": "Za",
        "NO": "Przeciw",
        "ABSTAIN": "Wstrzymał się",
        "ABSENT": "Nieobecny",
        "VOTE_VALID": "Oddał głos",
    }

    for bv in BENCHMARK_VOTINGS:
        v_map = benchmark_data.get((bv.sitting, bv.voting_number), {})
        mp_vote = v_map.get(mp_id, "ABSENT")
        impact_text = "brak wpływu (nieobecny)"

        if mp_vote == "YES":
            effect = bv.yes_effect
            if bv.axis == "x":
                x_contributions.append(effect)
                impact_text = "prawicowy (wolnorynkowy)" if effect > 0 else "lewicowy (socjalny)"
            else:
                y_contributions.append(effect)
                impact_text = "konserwatywny" if effect > 0 else "progresywny"
        elif mp_vote == "NO":
            effect = bv.no_effect
            if bv.axis == "x":
                x_contributions.append(effect)
                impact_text = "prawicowy (wolnorynkowy)" if effect > 0 else "lewicowy (socjalny)"
            else:
                y_contributions.append(effect)
                impact_text = "konserwatywny" if effect > 0 else "progresywny"
        elif mp_vote == "ABSTAIN":
            # Wstrzymanie się traktowane jako neutralne (0.0) z mniejszą wagą
            if bv.axis == "x":
                x_contributions.append(0.0)
            else:
                y_contributions.append(0.0)
            impact_text = "neutralny (wstrzymanie)"

        voting_details.append({
            "sitting": bv.sitting,
            "voting_number": bv.voting_number,
            "short_title": bv.short_title,
            "category": bv.category,
            "axis": bv.axis,
            "vote": mp_vote,
            "vote_label": vote_translations.get(mp_vote, mp_vote),
            "impact": impact_text,
            "description": bv.description,
        })

    avg_x = (sum(x_contributions) / len(x_contributions)) if x_contributions else 0.0
    avg_y = (sum(y_contributions) / len(y_contributions)) if y_contributions else 0.0

    return round(_clamp(avg_x), 2), round(_clamp(avg_y), 2), voting_details


def generate_fallback_descriptions(
    name: str,
    club_display_name: str,
    axis_x: float,
    axis_y: float,
    axis_label: str,
    voting_details: list[dict[str, Any]],
) -> dict[str, str]:
    """Generuje precyzyjny, rzeczowy opis na wypadek braku LLM lub dla trybu szybkiego."""
    econ_votes_for = [v["short_title"] for v in voting_details if v["axis"] == "x" and v["vote"] == "YES"]
    soc_votes_for = [v["short_title"] for v in voting_details if v["axis"] == "y" and v["vote"] == "YES"]
    
    if axis_x < -0.15:
        econ_desc = f"W sferze gospodarczej popiera państwo opiekuńcze i osłony socjalne (m.in. poparcie dla renty wdowiej i wakacji kredytowych)."
    elif axis_x > 0.15:
        econ_desc = f"W sferze gospodarczej promuje rozwiązania wolnorynkowe i ulgi dla przedsiębiorców (poparcie dla wakacji składkowych)."
    else:
        econ_desc = f"W sferze gospodarczej zajmuje stanowisko centrowe, łącząc wybrane elementy wolnorynkowe ze wsparciem socjalnym."

    if axis_y < -0.15:
        world_desc = f"W kwestiach światopoglądowych prezentuje stanowisko progresywne (m.in. głosowanie za refundacją in vitro czy dostępem do antykoncepcji awaryjnej)."
    elif axis_y > 0.15:
        world_desc = f"W kwestiach światopoglądowych konsekwentnie opowiada się za tradycyjnymi wartościami i konserwatywnym podejściem bioetycznym."
    else:
        world_desc = f"W sferze światopoglądowej prezentuje postawę umiarkowaną i centrową."

    summary = f"Na podstawie rzeczywistych głosowań w Sejmie X kadencji poseł {name} ({club_display_name}) plasuje się jako {axis_label}. {econ_desc} {world_desc}"
    
    return {
        "summary": summary,
        "economic_description": econ_desc,
        "worldview_description": world_desc,
    }


def analyze_with_ai(
    llm: ChatOpenAI,
    name: str,
    club: str,
    club_display_name: str,
    axis_x: float,
    axis_y: float,
    voting_details: list[dict[str, Any]],
) -> dict[str, str]:
    """Generuje syntezę profilu posła przy użyciu modelu AI."""
    summary_lines = []
    for v in voting_details:
        summary_lines.append(
            f"- {v['short_title']} [{v['category']}, oś {v['axis'].upper()}]: oddany głos '{v['vote_label']}' ({v['impact']})"
        )
    votings_summary = "\n".join(summary_lines)

    prompt = POLITICIAN_ANALYSIS_PROMPT.format(
        name=name,
        club=club,
        club_display_name=club_display_name,
        axis_x=axis_x,
        axis_y=axis_y,
        votings_summary=votings_summary,
    )

    try:
        response = llm.invoke(prompt)
        content = response.content if isinstance(response.content, str) else str(response.content)
        data = _extract_json_object(content)
        return {
            "summary": data.get("summary", "").strip(),
            "economic_description": data.get("economic_description", "").strip(),
            "worldview_description": data.get("worldview_description", "").strip(),
        }
    except Exception as exc:
        logger.warning(f"Błąd analizy AI dla {name}: {exc}. Używam generatora awaryjnego.")
        axis_label = derive_axis_label(axis_x, axis_y)
        return generate_fallback_descriptions(
            name=name,
            club_display_name=club_display_name,
            axis_x=axis_x,
            axis_y=axis_y,
            axis_label=axis_label,
            voting_details=voting_details,
        )


def calculate_and_store_all_politicians(
    use_ai: bool = False,
    limit_mps: int | None = None,
) -> None:
    log_header("Rozpoczynam analizę i pozycjonowanie polityków na scenie politycznej")
    voting_svc = SejmVotingService(current_term=10)
    
    log_info("1. Pobieram listę wszystkich posłów z Sejmu RP...")
    mps = voting_svc.get_deputies_list()
    if not mps:
        raise RuntimeError("Nie udało się pobrać listy posłów z API Sejmu.")
    log_success(f"Znaleziono {len(mps)} parlamentarzystów.")

    log_info("2. Pobieram dane 10 kluczowych głosowań referencyjnych...")
    benchmark_data = fetch_all_benchmark_votes(voting_svc)
    log_success("Pobrano dane głosowań referencyjnych.")

    llm: ChatOpenAI | None = None
    if use_ai:
        log_info(f"Inicjalizuję model LLM: {settings.chat_model}")
        llm = ChatOpenAI(model=settings.chat_model, temperature=0)

    calculated_at = datetime.now(timezone.utc).isoformat()
    positions_to_save: list[dict[str, Any]] = []

    target_mps = mps[:limit_mps] if limit_mps else mps
    log_info(f"3. Obliczam pozycje na scenie politycznej dla {len(target_mps)} posłów...")

    for i, mp in enumerate(target_mps, 1):
        mp_id = mp["id"]
        name = mp["first_last_name"]
        club = mp["club"]
        club_display_name = mp.get("club_display_name", club)
        photo_url = mp.get("photo_url", "")

        axis_x, axis_y, voting_details = compute_mp_raw_position(mp_id, benchmark_data)
        axis_label = derive_axis_label(axis_x, axis_y)

        if llm:
            ai_res = analyze_with_ai(
                llm=llm,
                name=name,
                club=club,
                club_display_name=club_display_name,
                axis_x=axis_x,
                axis_y=axis_y,
                voting_details=voting_details,
            )
        else:
            ai_res = generate_fallback_descriptions(
                name=name,
                club_display_name=club_display_name,
                axis_x=axis_x,
                axis_y=axis_y,
                axis_label=axis_label,
                voting_details=voting_details,
            )

        position_item = {
            "deputy_id": mp_id,
            "first_last_name": name,
            "club": club,
            "club_display_name": club_display_name,
            "photo_url": photo_url,
            "axis_x": axis_x,
            "axis_y": axis_y,
            "axis_label": axis_label,
            "summary": ai_res["summary"],
            "economic_description": ai_res["economic_description"],
            "worldview_description": ai_res["worldview_description"],
            "voting_details": voting_details,
            "calculated_at": calculated_at,
        }
        positions_to_save.append(position_item)

        if i % 50 == 0 or i == len(target_mps):
            log_info(f"Przetworzono {i}/{len(target_mps)} posłów (ostatni: {name} x={axis_x}, y={axis_y})")

    log_info("4. Zapisuję obliczone pozycje do bazy SQLite...")
    save_politician_positions(positions_to_save)
    log_success(f"Zapisano pomyślnie {len(positions_to_save)} pozycji polityków w bazie danych!")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analiza i obliczanie pozycji polityków na scenie politycznej na podstawie głosowań Sejmu X kadencji."
    )
    parser.add_argument(
        "--use-ai",
        action="store_true",
        help="Czy użyć OpenAI do generowania syntezy opisowej profilu każdego posła.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Opcjonalny limit liczby posłów do przetworzenia (np. do szybkiego testowania).",
    )
    args = parser.parse_args()

    calculate_and_store_all_politicians(use_ai=args.use_ai, limit_mps=args.limit)


if __name__ == "__main__":
    main()
