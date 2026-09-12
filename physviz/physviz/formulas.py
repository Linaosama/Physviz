"""Formula definitions and normalization."""
from dataclasses import dataclass


def normalize(value: str) -> str:
    return value.replace(" ", "").replace("·", "")


@dataclass(frozen=True)
class Formula:
    key: str
    kind: str
    display: str


FORMULAS = {
    normalize("mg"): Formula("mg", "mg", "mg"),
    normalize("E=mc²"): Formula("E=mc²", "black_hole", "E=mc²"),
    normalize("G=mv²/r"): Formula("G=mv²/r", "orbit_center", "G=mv²/r"),
    normalize("F=ma"): Formula("F=ma", "force", "F=ma"),
    normalize("p=mv"): Formula("p=mv", "momentum", "p=mv"),
    normalize("E=½mv²"): Formula("E=½mv²", "kinetic_energy", "E=½mv²"),
}


def recognize(labels: str):
    return FORMULAS.get(normalize(labels))
