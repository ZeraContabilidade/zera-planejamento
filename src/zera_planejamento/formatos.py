"""Formatação brasileira (R$, %, competência)."""
from __future__ import annotations

import math
import re
import unicodedata

import pandas as pd

MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


def _nan(v) -> bool:
    return v is None or (isinstance(v, float) and math.isnan(v))


def brl(v, casas: int = 2) -> str:
    if _nan(v):
        return "–"
    s = f"{abs(v):,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"-R$ {s}" if v < 0 else f"R$ {s}"


def brl_curto(v) -> str:
    """R$ compacto para cartões: 1.111.500 → "R$ 1,11 mi"; 183.448 → "R$ 183 mil"; 18.344 → "R$ 18,3 mil"."""
    if _nan(v):
        return "–"
    a = abs(v)
    if a >= 1_000_000:
        txt = f"{a / 1_000_000:,.2f} mi"
    elif a >= 100_000:
        txt = f"{a / 1_000:,.0f} mil"
    elif a >= 10_000:
        txt = f"{a / 1_000:,.1f} mil"
    else:
        return brl(v, 0)
    txt = txt.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"-R$ {txt}" if v < 0 else f"R$ {txt}"


def pct(v, casas: int = 2) -> str:
    if _nan(v):
        return "–"
    return f"{v * 100:.{casas}f}%".replace(".", ",")


def comp(p: pd.Period) -> str:
    return f"{MESES[p.month - 1]}/{str(p.year)[2:]}"


def slug(texto: str) -> str:
    t = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", t.lower()).strip("_")
