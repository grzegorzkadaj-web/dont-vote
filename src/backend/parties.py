from dataclasses import dataclass
from typing import Literal

PartyKey = Literal["po", "kkp", "konfederacja"]


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
}
