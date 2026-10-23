import json
import logging
import re
import urllib.parse
import urllib.request
from collections import defaultdict
from functools import lru_cache
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

SEJM_API_BASE = "https://api.sejm.gov.pl/sejm"
ELI_API_BASE = "https://api.sejm.gov.pl/eli"

CLUB_DISPLAY_NAMES: dict[str, str] = {
    "KO": "Koalicja Obywatelska",
    "PiS": "Prawo i Sprawiedliwość",
    "Konfederacja": "Konfederacja",
    "Konfederacja_KP": "Konfederacja Korony Polskiej",
    "PSL-TD": "PSL - Trzecia Droga",
    "PSL": "PSL - Trzecia Droga",
    "Polska2050": "Polska 2050 - Trzecia Droga",
    "Lewica": "Lewica",
    "Nowa_Lewica": "Lewica",
    "Razem": "Partia Razem",
    "Centrum": "Klub Centrum",
    "RozwojPlus": "Rozwój Plus",
    "Demokracja": "Demokracja Bezpośrednia",
    "niez.": "Posłowie niezrzeszeni",
}

PRIORITY_CLUBS = [
    "KO",
    "PiS",
    "Konfederacja",
    "PSL-TD",
    "PSL",
    "Polska2050",
    "Lewica",
    "Nowa_Lewica",
    "Razem",
    "Konfederacja_KP",
]

TOPIC_SYNONYMS: dict[str, list[str]] = {
    "in vitro": ["in vitro", "niepłodn", "świadczeniach opieki zdrowotnej"],
    "niepłodność": ["in vitro", "niepłodn", "świadczeniach opieki zdrowotnej"],
    "aborcja": ["ciąży", "przerywaniu ciąży", "świadomym rodzicielstwie"],
    "aborcji": ["ciąży", "przerywaniu ciąży"],
    "pigułka dzień po": ["antykoncepcj", "farmaceutyczn", "recept"],
    "antykoncepcja": ["antykoncepcj", "farmaceutyczn"],
    "wakacje składkowe": ["ubezpieczeń społecznych", "wakacj", "składk"],
    "wakacje od zus": ["ubezpieczeń społecznych", "wakacj", "składk"],
    "składka zdrowotna": ["składk", "świadczeniach opieki zdrowotnej", "zdrowotn"],
    "kredyt 0%": ["kredytobiorc", "kredyt", "mieszkaniow"],
    "kredyt 2%": ["kredytobiorc", "kredyt", "mieszkaniow"],
    "kredyt na start": ["kredytobiorc", "kredyt", "mieszkaniow"],
    "kredyt mieszkaniowy": ["kredytobiorc", "kredyt", "mieszkaniow"],
    "mieszkalnictwo": ["mieszkan", "kredytobiorc", "lokal"],
    "mieszkania": ["mieszkan", "kredytobiorc", "lokal"],
    "cpk": ["centralny port", "komunikacyjn"],
    "renta wdowia": ["wdowi", "rent", "emerytur"],
    "renty wdowiej": ["wdowi", "rent", "emerytur"],
    "emerytury": ["emerytur", "rent", "emerytaln"],
    "zasiłek pogrzebowy": ["zasiłku pogrzebowego", "zasiłek pogrzebowy", "emeryturach i rentach"],
    "ceny prądu": ["energi", "paliw gazowych", "ciepła"],
    "ceny energii": ["energi", "paliw gazowych", "ciepła"],
    "zamrożenie cen": ["energi", "paliw gazowych", "ciepła"],
    "handel w niedziele": ["ograniczeniu handlu", "niedziel"],
    "handel w niedzielę": ["ograniczeniu handlu", "niedziel"],
    "edukacja": ["oświat", "szkol", "nauczyciel", "edukac"],
    "nauczyciele": ["karty nauczyciela", "nauczyciel", "oświat"],
    "obronność": ["obron", "wojsk", "sił zbrojnych", "uzbrojen"],
    "rolnictwo": ["roln", "gospodarstw", "wieś"],
    "ukraina": ["pomocy obywatelom ukrainy", "ukrain"],
    "trybunał konstytucyjny": ["trybunale konstytucyjnym", "trybunał"],
    "sądownictwo": ["krajowej radzie sądownictwa", "sąd"],
}


def _http_get_json(url: str, timeout: float = 20.0, max_retries: int = 3) -> Any:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "PoliticsApp/1.0 (Mozilla/5.0)",
            "Accept": "application/json",
        },
    )
    last_err = None
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            last_err = exc
    raise last_err


def expand_search_terms(query: str) -> list[str]:
    q_norm = query.strip().lower()
    terms: list[str] = []

    # 1. Match synonym map
    for k, syns in TOPIC_SYNONYMS.items():
        if k in q_norm or q_norm in k:
            for s in syns:
                if s not in terms:
                    terms.append(s)

    # 2. Add raw query if >= 3 characters
    if len(q_norm) >= 3 and q_norm not in terms:
        terms.append(q_norm)

    # 3. Add Polish word stems
    words = [w.strip() for w in re.split(r"[\s,\.\?!]+", q_norm) if len(w.strip()) >= 3]
    for w in words:
        if len(w) > 4:
            stem = w[:-1] if w.endswith(("a", "e", "y", "i", "u", "ą", "ę", "o")) else w
            if stem not in terms:
                terms.append(stem)
        else:
            if w not in terms:
                terms.append(w)

    return terms


class SejmVotingService:
    def __init__(self, current_term: int = 10):
        self.term = current_term
        self._voting_details_cache: dict[str, dict[str, Any]] = {}
        self._process_cache: dict[str, dict[str, Any]] = {}
        self._search_cache: dict[str, list[dict[str, Any]]] = {}

    def get_voting_details(self, sitting: int, voting_num: int) -> dict[str, Any]:
        key = f"{self.term}_{sitting}_{voting_num}"
        if key in self._voting_details_cache:
            return self._voting_details_cache[key]

        url = f"{SEJM_API_BASE}/term{self.term}/votings/{sitting}/{voting_num}"
        try:
            data = _http_get_json(url)
            self._voting_details_cache[key] = data
            return data
        except Exception as exc:
            logger.warning("Failed to fetch voting details %s: %s", key, exc)
            return {}

    def get_process_details(self, print_number: str) -> dict[str, Any]:
        key = f"{self.term}_{print_number}"
        if key in self._process_cache:
            return self._process_cache[key]

        url = f"{SEJM_API_BASE}/term{self.term}/processes/{print_number}"
        try:
            data = _http_get_json(url)
            self._process_cache[key] = data
            return data
        except Exception as exc:
            logger.warning("Failed to fetch process %s: %s", key, exc)
            return {}

    def search_acts_and_votes(self, query: str, limit: int = 8) -> list[dict[str, Any]]:
        cache_key = f"{query.strip().lower()}_{limit}"
        if cache_key in self._search_cache:
            return self._search_cache[cache_key]

        search_terms = expand_search_terms(query)
        raw_votings: list[dict[str, Any]] = []
        seen_voting_keys: set[str] = set()

        for term_keyword in search_terms:
            quoted = urllib.parse.quote(term_keyword)
            url = f"{SEJM_API_BASE}/term{self.term}/votings/search?title={quoted}&limit=15"
            try:
                results = _http_get_json(url)
                if isinstance(results, list):
                    for v in results:
                        vk = f"{v.get('sitting')}_{v.get('votingNumber')}"
                        if vk not in seen_voting_keys:
                            seen_voting_keys.add(vk)
                            raw_votings.append(v)
            except Exception as exc:
                logger.debug("Voting search error for '%s': %s", term_keyword, exc)

            if len(raw_votings) >= 25:
                break

        # Also search ELI if few or no votings found
        if len(raw_votings) < 3:
            for term_keyword in search_terms[:2]:
                quoted = urllib.parse.quote(term_keyword)
                eli_url = f"{ELI_API_BASE}/acts/search?title={quoted}&limit=5"
                try:
                    eli_data = _http_get_json(eli_url)
                    items = eli_data.get("items", []) if isinstance(eli_data, dict) else []
                    for act in items:
                        # try to find prints
                        for p in act.get("prints", []):
                            p_url = f"{SEJM_API_BASE}/term{self.term}/processes/{p}"
                            try:
                                proc = _http_get_json(p_url)
                                for stage in proc.get("stages", []):
                                    if stage.get("voting"):
                                        v = stage["voting"]
                                        vk = f"{v.get('sitting')}_{v.get('votingNumber')}"
                                        if vk not in seen_voting_keys:
                                            seen_voting_keys.add(vk)
                                            raw_votings.append(v)
                            except Exception:
                                pass
                except Exception as exc:
                    logger.debug("ELI search error for '%s': %s", term_keyword, exc)

        if not raw_votings:
            self._search_cache[cache_key] = []
            return []

        # Group votings by act / print number
        # A bill may have dozens of votes (amendments etc.), we want to prioritize:
        # 1. Final passage ("głosowanie nad całością projektu", "uchwalenie", "III czytanie")
        # 2. Main rejection motions ("odrzucenie w pierwszym czytaniu" or "odrzucenie w całości")
        bills: dict[str, dict[str, Any]] = {}

        for v in raw_votings:
            title = v.get("title") or ""
            topic = (v.get("topic") or "").lower()
            desc = (v.get("description") or "").lower()

            # Find print number
            m = re.search(r"druk(?:i|\xf3w)?\s+nr\s+([0-9]+)", title, re.IGNORECASE)
            print_num = m.group(1) if m else f"v_{v.get('sitting')}_{v.get('votingNumber')}"

            is_final = any(
                term in topic or term in desc
                for term in [
                    "całośc",
                    "całość",
                    "uchwalen",
                    "3. czyt",
                    "iii czyt",
                    "przyjęcie projektu",
                    "całością projektu",
                ]
            )
            is_rejection = "odrzucen" in topic or "odrzucen" in desc
            
            # Score relevance
            score = 10 if is_final else (5 if is_rejection else 1)

            # Extra weight if keyword from query is directly in title
            for st in search_terms[:2]:
                if st in title.lower():
                    score += 2

            if print_num not in bills or score > bills[print_num]["score"]:
                bills[print_num] = {
                    "score": score,
                    "voting": v,
                    "print_num": print_num if m else None,
                    "all_votings": [v],
                }
            else:
                bills[print_num]["all_votings"].append(v)

        # Select top bills
        sorted_bills = sorted(
            bills.values(),
            key=lambda b: (b["score"], b["voting"].get("date", "")),
            reverse=True,
        )[:limit]

        final_acts: list[dict[str, Any]] = []

        for item in sorted_bills:
            v = item["voting"]
            sitting = v.get("sitting")
            voting_num = v.get("votingNumber")
            print_num = item["print_num"]

            act_title = v.get("title", "")
            # Clean act title: strip "Pkt. X Sprawozdanie Komisji o..."
            cleaned_title = re.sub(
                r"^Pkt\.?\s*\d+[\.,\d\s]*\s*(Sprawozdanie Komisji o|Pierwsze czytanie|Przedstawiony przez[^\:]+:)?\s*",
                "",
                act_title,
                flags=re.IGNORECASE,
            ).strip()

            short_desc = v.get("description") or v.get("topic") or ""
            passed = v.get("yes", 0) > v.get("no", 0)
            display_address: Optional[str] = None
            eli_code: Optional[str] = None
            doc_type: str = "projekt ustawy"
            links: dict[str, str] = {
                "sejm_voting_pdf": f"{SEJM_API_BASE}/term{self.term}/votings/{sitting}/{voting_num}/pdf"
            }

            if print_num:
                proc = self.get_process_details(print_num)
                if proc:
                    if proc.get("titleFinal"):
                        cleaned_title = proc.get("titleFinal")
                    elif proc.get("title"):
                        cleaned_title = proc.get("title")

                    if proc.get("description"):
                        short_desc = proc.get("description")

                    if "passed" in proc:
                        passed = proc["passed"]

                    display_address = proc.get("displayAddress")
                    eli_code = proc.get("ELI")
                    doc_type = proc.get("documentType", doc_type)

                    if proc.get("links"):
                        for link in proc["links"]:
                            rel = link.get("rel", "link")
                            links[rel] = link.get("href")

            # Fallback description if still empty
            if not short_desc or len(short_desc.strip()) < 5:
                short_desc = f"Głosowanie sejmowe dotyczące: {cleaned_title}"

            # Capitalize first letter of description
            if short_desc:
                short_desc = short_desc[0].upper() + short_desc[1:]

            # Fetch voting details to get per-club breakdown
            v_details = self.get_voting_details(sitting, voting_num)
            votes_list = v_details.get("votes", [])

            by_club: dict[str, dict[str, int]] = defaultdict(
                lambda: {"YES": 0, "NO": 0, "ABSTAIN": 0, "ABSENT": 0, "TOTAL": 0}
            )

            for vote_item in votes_list:
                club_raw = vote_item.get("club") or "niez."
                vote_val = vote_item.get("vote") or "ABSENT"

                by_club[club_raw]["TOTAL"] += 1
                if vote_val in by_club[club_raw]:
                    by_club[club_raw][vote_val] += 1
                else:
                    by_club[club_raw]["ABSENT"] += 1

            parties_stats = []
            for club_id, stats in by_club.items():
                tot = stats["TOTAL"]
                yes = stats["YES"]
                no = stats["NO"]
                abstain = stats["ABSTAIN"]
                absent = stats["ABSENT"]

                # Determine dominant stance
                if yes > no and yes > abstain and yes > absent:
                    stance = "ZA"
                elif no > yes and no > abstain and no > absent:
                    stance = "PRZECIW"
                elif abstain >= yes and abstain >= no and abstain > absent:
                    stance = "WSTRZYMAŁ SIĘ"
                elif absent > (yes + no + abstain):
                    stance = "NIEOBECNI"
                else:
                    stance = "PODZIELENI"

                parties_stats.append({
                    "club_id": club_id,
                    "club_name": CLUB_DISPLAY_NAMES.get(club_id, club_id),
                    "yes": yes,
                    "no": no,
                    "abstain": abstain,
                    "absent": absent,
                    "total": tot,
                    "stance": stance,
                    "percent_yes": round((yes / tot) * 100, 1) if tot > 0 else 0.0,
                    "percent_no": round((no / tot) * 100, 1) if tot > 0 else 0.0,
                    "percent_abstain": round((abstain / tot) * 100, 1) if tot > 0 else 0.0,
                })

            # Sort parties: Priority clubs first
            def club_sort(p: dict[str, Any]) -> tuple[int, int]:
                cid = p["club_id"]
                if cid in PRIORITY_CLUBS:
                    return (0, PRIORITY_CLUBS.index(cid))
                return (1, -p["total"])

            parties_stats.sort(key=club_sort)

            act_entry = {
                "id": f"act-{self.term}-{sitting}-{voting_num}",
                "act_name": cleaned_title,
                "short_description": short_desc,
                "document_type": doc_type,
                "sitting": sitting,
                "voting_number": voting_num,
                "date": v.get("date"),
                "topic": v.get("topic"),
                "passed": passed,
                "display_address": display_address,
                "eli": eli_code,
                "links": links,
                "total_votes": {
                    "yes": v.get("yes", 0),
                    "no": v.get("no", 0),
                    "abstain": v.get("abstain", 0),
                    "absent": v.get("notParticipating", 0),
                    "total": v.get("totalVoted", 0) + v.get("notParticipating", 0),
                },
                "parties": parties_stats,
            }
            final_acts.append(act_entry)

        self._search_cache[cache_key] = final_acts
        return final_acts

    def get_deputies_list(self) -> list[dict[str, Any]]:
        url = f"{SEJM_API_BASE}/term{self.term}/MP"
        try:
            data = _http_get_json(url)
            if not isinstance(data, list):
                return []

            active_mps = [m for m in data if m.get("active", True)]
            active_mps.sort(key=lambda m: m.get("lastFirstName", ""))

            result = []
            for m in active_mps:
                mp_id = m.get("id")
                club_id = m.get("club") or "niez."
                club_name = CLUB_DISPLAY_NAMES.get(club_id, club_id)
                result.append({
                    "id": mp_id,
                    "first_last_name": m.get("firstLastName", ""),
                    "last_first_name": m.get("lastFirstName", ""),
                    "club": club_id,
                    "club_display_name": club_name,
                    "district_name": m.get("districtName"),
                    "district_num": m.get("districtNum"),
                    "email": m.get("email"),
                    "photo_url": f"{SEJM_API_BASE}/term{self.term}/MP/{mp_id}/photo-mini",
                    "active": m.get("active", True),
                })
            return result
        except Exception as exc:
            logger.error("Failed to fetch deputies list: %s", exc)
            return []

    def get_deputy_details(self, mp_id: int) -> dict[str, Any]:
        url = f"{SEJM_API_BASE}/term{self.term}/MP/{mp_id}"
        try:
            data = _http_get_json(url)
            club_id = data.get("club") or "niez."
            return {
                "id": mp_id,
                "first_last_name": data.get("firstLastName", ""),
                "last_first_name": data.get("lastFirstName", ""),
                "club": club_id,
                "club_display_name": CLUB_DISPLAY_NAMES.get(club_id, club_id),
                "district_name": data.get("districtName"),
                "district_num": data.get("districtNum"),
                "email": data.get("email"),
                "photo_url": f"{SEJM_API_BASE}/term{self.term}/MP/{mp_id}/photo-mini",
                "active": data.get("active", True),
            }
        except Exception as exc:
            logger.error("Failed to fetch deputy %s: %s", mp_id, exc)
            return {}

    def get_total_act_proposals(self) -> int:
        """Pobiera całkowitą liczbę poselskich projektów ustaw w obecnej kadencji."""
        try:
            # Liczba druków z tytułem 'poselski projekt ustawy'
            url = f"{SEJM_API_BASE}/term{self.term}/prints"
            prints = _http_get_json(url)
            if isinstance(prints, list):
                count = sum(
                    1 for p in prints if "poselski projekt ustawy" in (p.get("title") or "").lower()
                )
                if count > 0:
                    return count
        except Exception as exc:
            logger.warning("Failed to count prints for act proposals: %s", exc)
        return 358

    def get_deputy_activity_stats(self, mp_id: int) -> dict[str, Any]:
        deputy = self.get_deputy_details(mp_id)
        club_id = deputy.get("club", "niez.")
        party_name = deputy.get("club_display_name", CLUB_DISPLAY_NAMES.get(club_id, club_id))

        # 1. Statystyki głosowań z /sejm/term{term}/MP/{id}/votings/stats
        stats_url = f"{SEJM_API_BASE}/term{self.term}/MP/{mp_id}/votings/stats"
        total_votings = 0
        voted_votings = 0
        unexcused_absences = 0
        excused_absences = 0
        unexcused_days = 0

        try:
            stats_data = _http_get_json(stats_url)
            if isinstance(stats_data, list):
                for row in stats_data:
                    num_votings = row.get("numVotings", 0)
                    num_voted = row.get("numVoted", 0)
                    num_missed = row.get("numMissed", 0)
                    excused = bool(row.get("absenceExcuse", False))

                    total_votings += num_votings
                    voted_votings += num_voted

                    if num_missed > 0:
                        if excused:
                            excused_absences += num_missed
                        else:
                            unexcused_absences += num_missed
                            unexcused_days += 1
        except Exception as exc:
            logger.warning("Failed to fetch voting stats for MP %s: %s", mp_id, exc)

        attendance_rate = (
            round((voted_votings / total_votings) * 100, 1) if total_votings > 0 else 0.0
        )

        # 2. Liczba projektów ustaw (poselskich projektów ustaw w obecnej kadencji)
        act_proposals_count = self.get_total_act_proposals()

        # 3. Interpelacje i zapytania poselskie dla danego posła
        padded_id = f"{mp_id:03d}"
        interpellations_count = 0
        written_questions_count = 0

        try:
            req = urllib.request.Request(
                f"{SEJM_API_BASE}/term{self.term}/interpellations?from={padded_id}&limit=1",
                headers={"User-Agent": "PoliticsApp/1.0", "Accept": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                cr = resp.headers.get("Content-Range", "")
                if "/" in cr:
                    interpellations_count = int(cr.split("/")[-1])
        except Exception:
            pass

        try:
            req = urllib.request.Request(
                f"{SEJM_API_BASE}/term{self.term}/writtenQuestions?from={padded_id}&limit=1",
                headers={"User-Agent": "PoliticsApp/1.0", "Accept": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                cr = resp.headers.get("Content-Range", "")
                if "/" in cr:
                    written_questions_count = int(cr.split("/")[-1])
        except Exception:
            pass

        return {
            "deputy_id": mp_id,
            "total_votings": total_votings,
            "voted_votings": voted_votings,
            "unexcused_absences": unexcused_absences,
            "unexcused_absence_days": unexcused_days,
            "excused_absences": excused_absences,
            "attendance_rate": attendance_rate,
            "club_id": club_id,
            "party_name": party_name,
            "act_proposals_count": act_proposals_count,
            "interpellations_count": interpellations_count,
            "written_questions_count": written_questions_count,
            "term": self.term,
        }

