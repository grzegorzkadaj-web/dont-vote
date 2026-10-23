import json
import logging
from dataclasses import dataclass
from typing import Any, List, Optional

logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class BenchmarkVoting:
    sitting: int
    voting_number: int
    short_title: str
    category: str
    axis: str  # "x" (economic/social) or "y" (social/worldview)
    yes_effect: float
    no_effect: float
    description: str

# 10 key parliamentary votes in Sejm X term representing economic and worldview axes
BENCHMARK_VOTINGS: list[BenchmarkVoting] = [
    BenchmarkVoting(
        sitting=1,
        voting_number=40,
        short_title="Finansowanie procedury in vitro z budżetu państwa",
        category="Światopogląd i bioetyka",
        axis="y",
        yes_effect=-0.8,  # progresywny
        no_effect=0.8,    # konserwatywny
        description="Głosowanie nad całością obywatelskiego projektu ustawy o finansowaniu in vitro z budżetu państwa.",
    ),
    BenchmarkVoting(
        sitting=6,
        voting_number=14,
        short_title="Dostępność tabletki 'dzień po' bez recepty",
        category="Prawa reprodukcyjne",
        axis="y",
        yes_effect=-0.8,
        no_effect=0.8,
        description="Nowelizacja Prawa farmaceutycznego umożliwiająca dostęp do antykoncepcji awaryjnej od 15. roku życia bez recepty.",
    ),
    BenchmarkVoting(
        sitting=15,
        voting_number=9,
        short_title="Dekryminalizacja i depenalizacja pomocy przy aborcji",
        category="Prawa reprodukcyjne i karne",
        axis="y",
        yes_effect=-1.0,
        no_effect=1.0,
        description="Projekt nowelizacji Kodeksu karnego wyłączający karalność za pomocnictwo w przerwaniu ciąży za zgodą kobiety.",
    ),
    BenchmarkVoting(
        sitting=10,
        voting_number=13,
        short_title="Uznanie języka śląskiego za język regionalny",
        category="Mniejszości i tożsamość regionalna",
        axis="y",
        yes_effect=-0.6,
        no_effect=0.6,
        description="Ustawa o mniejszościach narodowych i etnicznych nadająca śląskiemu status oficjalnego języka regionalnego.",
    ),
    BenchmarkVoting(
        sitting=22,
        voting_number=150,
        short_title="Odrzucenie projektu zakazu hodowli zwierząt na futra",
        category="Prawa zwierząt i ekologia",
        axis="y",
        yes_effect=0.7,   # Za odrzuceniem zakazu = konserwatywne/tradycyjne
        no_effect=-0.7,  # Przeciw odrzuceniu (za zakazem futer) = progresywne
        description="Wniosek o odrzucenie w I czytaniu obywatelskiego projektu zakazu hodowli zwierząt futerkowych.",
    ),
    BenchmarkVoting(
        sitting=11,
        voting_number=16,
        short_title="Wakacje składkowe od ZUS dla mikroprzedsiębiorców",
        category="Gospodarka i podatki",
        axis="x",
        yes_effect=0.7,   # Wolnorynkowe/ulga dla firm
        no_effect=-0.9,  # Lewica socjalna (przeciw uszczuplaniu Funduszu Ubezpieczeń Społecznych)
        description="Ustawa zwalniająca mikroprzedsiębiorców z opłacania składki na ZUS przez jeden miesiąc w roku.",
    ),
    BenchmarkVoting(
        sitting=16,
        voting_number=63,
        short_title="Wprowadzenie renty wdowiej",
        category="Świadczenia socjalne i emerytury",
        axis="x",
        yes_effect=-0.8,  # Państwo socjalne/opiekuńcze
        no_effect=0.9,    # Wolny rynek/ograniczenie wydatków budżetowych
        description="Obywatelski projekt ustawy umożliwiający łączenie renty rodzinnej po zmarłym małżonku z własną emeryturą.",
    ),
    BenchmarkVoting(
        sitting=9,
        voting_number=18,
        short_title="Rządowe wakacje kredytowe i ochrona kredytobiorców",
        category="Rynek finansowy i pomoc kredytobiorcom",
        axis="x",
        yes_effect=-0.7,  # Regulacja rynku/wsparcie socjalne kosztem banków
        no_effect=0.9,    # Wolny rynek finansowy
        description="Przedłużenie ustawowych wakacji kredytowych oraz wsparcie z Funduszu Wsparcia Kredytobiorców.",
    ),
    BenchmarkVoting(
        sitting=14,
        voting_number=29,
        short_title="Odrzucenie projektu liberalizacji handlu w niedziele",
        category="Rynek pracy i prawa pracownicze",
        axis="x",
        yes_effect=-0.8,  # Za odrzuceniem liberalizacji = ochrona pracowników handlu (socjalne)
        no_effect=0.8,    # Przeciw odrzuceniu (za niedzielami handlowymi) = wolny rynek
        description="Głosowanie nad wnioskiem o odrzucenie projektu ustawy przywracającej dwie niedziele handlowe w miesiącu.",
    ),
    BenchmarkVoting(
        sitting=5,
        voting_number=28,
        short_title="Przedłużenie wsparcia i osłon podatkowych dla uchodźców z Ukrainy",
        category="Polityka migracyjna i socjalna",
        axis="x",
        yes_effect=-0.5,  # Solidarność państwowa i socjalna
        no_effect=0.8,    # Ograniczenie transferów socjalnych dla cudzoziemców
        description="Ustawa przedłużająca legalny pobyt i świadczenia socjalne dla obywateli Ukrainy uciekających przed wojną.",
    ),
]
