import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

PartyKey = Literal["po", "kkp", "konfederacja", "razem", "psl", "pis"]


@dataclass(frozen=True)
class PartyConfig:
    key: PartyKey
    display_name: str
    index_name: str
    programme_url: str
    axis_x: float
    axis_y: float
    axis_label: str


PARTY_CONFIGS: dict[PartyKey, PartyConfig] = {
    "po": PartyConfig(
        key="po",
        display_name="Platforma Obywatelska",
        index_name="parties-po-index",
        programme_url="https://platforma.org/upload/document/201/attachments/413/100%20konkretow-pdf.pdf",
        axis_x=-0.1,
        axis_y=0.2,
        axis_label="centro-liberalna",
    ),
    "kkp": PartyConfig(
        key="kkp",
        display_name="Konfederacja Korony Polskiej",
        index_name="parties-kkp-index",
        programme_url="https://konfederacjakoronypolskiej.pl/wp-content/uploads/2023/03/Program-KKP-internet.pdf",
        axis_x=0.9,
        axis_y=0.5,
        axis_label="narodowo-konserwatywna",
    ),
    "konfederacja": PartyConfig(
        key="konfederacja",
        display_name="Konfederacja",
        index_name="parties-konfederacja-index",
        programme_url="https://konfederacja.pl/app/uploads/Konfederacja_WiN_Program_2023-1.pdf",
        axis_x=0.7,
        axis_y=0.3,
        axis_label="konserwatywno-liberalna",
    ),
    "razem": PartyConfig(
        key="razem",
        display_name="Partia Razem",
        index_name="parties-razem-index",
        programme_url="https://partiarazem.pl/deklaracja-programowa",
        axis_x=-0.8,
        axis_y=-0.2,
        axis_label="socjaldemokratyczna",
    ),
    "psl": PartyConfig(
        key="psl",
        display_name="Polskie Stronnictwo Ludowe",
        index_name="parties-psl-index",
        programme_url="https://www.psl.pl/wp-content/uploads/2023/09/Program-PSL.pdf",
        axis_x=0.0,
        axis_y=0.0,
        axis_label="ludowo-centrowa",
    ),
    "pis": PartyConfig(
        key="pis",
        display_name="Prawo i Sprawiedliwość (PiS)",
        index_name="parties-pis-index",
        programme_url="https://bip.pis.org.pl/program-partii",
        axis_x=0.8,
        axis_y=0.4,
        axis_label="narodowo-konserwatywna",
    ),
}


def load_calculated_positions(
    path: str | Path,
) -> dict[PartyKey, dict[str, float | str]]:
    file_path = Path(path)
    if not file_path.exists():
        return {}

    with file_path.open(encoding="utf-8") as file:
        payload = json.load(file)

    parties_payload = payload.get("parties")
    if not isinstance(parties_payload, dict):
        return {}

    positions: dict[PartyKey, dict[str, float | str]] = {}
    for key in PARTY_CONFIGS:
        raw = parties_payload.get(key)
        if not isinstance(raw, dict):
            continue

        axis_x = raw.get("axis_x")
        axis_y = raw.get("axis_y")
        axis_label = raw.get("axis_label")
        if not isinstance(axis_x, (int, float)):
            continue
        if not isinstance(axis_y, (int, float)):
            continue
        if not isinstance(axis_label, str) or not axis_label.strip():
            continue

        positions[key] = {
            "axis_x": max(-1.0, min(1.0, float(axis_x))),
            "axis_y": max(-1.0, min(1.0, float(axis_y))),
            "axis_label": axis_label.strip(),
        }

    return positions
