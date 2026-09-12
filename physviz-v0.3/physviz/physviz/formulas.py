"""Recognized formula chips."""
from dataclasses import dataclass


def normalize(value):
    return str(value).replace(" ", "").replace("·", "")


@dataclass(frozen=True)
class Formula:
    key: str
    kind: str
    display: str


FORMULAS = {
    normalize("mg"): Formula("mg", "mg", "mg"),
    normalize("E=mc²"): Formula("E=mc²", "black_hole", "E=mc²"),
    normalize("G=mv²/r"): Formula("G=mv²/r", "star", "G=mv²/r"),
    normalize("F=ma"): Formula("F=ma", "force", "F=ma"),
    normalize("p=mv"): Formula("p=mv", "momentum", "p=mv"),
    normalize("E=½mv²"): Formula("E=½mv²", "energy", "E=½mv²"),
    normalize("f=μN"): Formula("f=μN", "friction", "f=μN"),
    normalize("Ep=mgh"): Formula("E_p=mgh", "potential", "E_p=mgh"),
    normalize("E_p=mgh"): Formula("E_p=mgh", "potential", "E_p=mgh"),
    normalize("v=v0+at"): Formula("v=v_0+at", "velocity_time", "v=v_0+at"),
    normalize("F=GMm/r²"): Formula("F=GMm/r²", "gravity_force", "F=GMm/r²"),
    normalize("W=Fs"): Formula("W=Fs", "work", "W=Fs"),
}


def recognize(value):
    return FORMULAS.get(normalize(value))
