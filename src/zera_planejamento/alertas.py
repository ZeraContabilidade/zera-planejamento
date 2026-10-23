"""Alertas de conferência: CRÍTICO (não usar até resolver), ATENÇÃO (revisar) e INFO."""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

NIVEIS = ("CRÍTICO", "ATENÇÃO", "INFO")


@dataclass(frozen=True)
class Alerta:
    nivel: str
    origem: str
    mensagem: str


@dataclass
class Alertas:
    itens: list[Alerta] = field(default_factory=list)

    def add(self, nivel: str, origem: str, mensagem: str) -> None:
        a = Alerta(nivel if nivel in NIVEIS else "INFO", origem, mensagem)
        if a not in self.itens:
            self.itens.append(a)

    def critico(self, origem: str, msg: str) -> None:
        self.add("CRÍTICO", origem, msg)

    def atencao(self, origem: str, msg: str) -> None:
        self.add("ATENÇÃO", origem, msg)

    def info(self, origem: str, msg: str) -> None:
        self.add("INFO", origem, msg)

    def estender(self, outros: "Alertas") -> None:
        for a in outros.itens:
            if a not in self.itens:
                self.itens.append(a)

    def contagem(self) -> dict[str, int]:
        return {n: sum(1 for a in self.itens if a.nivel == n) for n in NIVEIS}

    def como_df(self) -> pd.DataFrame:
        ordem = {n: i for i, n in enumerate(NIVEIS)}
        df = pd.DataFrame([a.__dict__ for a in self.itens], columns=["nivel", "origem", "mensagem"])
        return df.sort_values("nivel", key=lambda s: s.map(ordem), kind="stable").reset_index(drop=True)
