"""
Simulador "E se…": quanto cada regime pagaria nos próximos 12 meses se a receita, a folha, o pró-labore ou os
custos mudassem.

1. ``ano_base``: projeção dos próximos 12 meses (cenário Neutro, método do cadastro) anexada ao histórico.
2. ``simular``: aplica os ajustes **só nos meses projetados** e roda o motor na série inteira (RBT12, Fator R,
   trimestres e regras de cada ano saem certos):
   - receita: todas as receitas × (1 + ajuste); os itens que acompanham a receita na projeção (custos, insumos,
     fretes, devoluções, ICMS e ISS) acompanham também;
   - folha: salários e FGTS × (1 + ajuste);
   - pró-labore: valor mensal informado (total dos sócios);
   - custos e despesas: × (1 + ajuste), além do efeito da receita sobre os custos.
O motor continua sendo a única fonte dos números; aqui só se monta a base simulada.
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass

import pandas as pd

from .alertas import Alertas
from .base import RECEITAS, BaseMensal
from .calculo import calcular
from .cliente import Cliente, Projecao
from .projecao import VARIAVEIS, projetar


@dataclass(frozen=True)
class Ajustes:
    receita: float = 0.0           # −0,30 = receita 30% menor
    folha: float = 0.0
    custos: float = 0.0
    pro_labore: float | None = None    # mensal, total dos sócios (None = como na projeção)


def ano_base(base: BaseMensal, cliente: Cliente) -> tuple[BaseMensal, pd.PeriodIndex]:
    """Histórico + 12 meses projetados (Neutro) e os meses projetados."""
    cli = dataclasses.replace(cliente, projecao=dataclasses.replace(cliente.projecao, meses=12, otimista=0.0,
                                                                    pessimista=0.0))
    neutro = projetar(base, cli, Alertas())["Neutro"]
    return neutro.base_completa, neutro.meses


def aplicar(completa: BaseMensal, meses: pd.PeriodIndex, aj: Ajustes) -> BaseMensal:
    sim = completa.copia()
    d = sim.dados
    sel = d.index.isin(meses)
    for col in RECEITAS + VARIAVEIS:
        d.loc[sel, col] = d.loc[sel, col] * (1 + aj.receita)
    for col in ("custos", "despesas"):
        d.loc[sel, col] = d.loc[sel, col] * (1 + aj.custos)
    for col in ("salarios", "fgts"):
        d.loc[sel, col] = d.loc[sel, col] * (1 + aj.folha)
    if aj.pro_labore is not None:
        d.loc[sel, "pro_labore"] = aj.pro_labore
    return sim


def simular(completa: BaseMensal, meses: pd.PeriodIndex, cliente: Cliente, aj: Ajustes) -> dict:
    """Resumo por regime (antes e depois do ajuste) nos meses projetados, e o Fator R final."""
    saida = {}
    for nome, b in (("base", completa), ("simulado", aplicar(completa, meses, aj))):
        r = calcular(b, cliente, Alertas())
        saida[nome] = r.resumo(meses)
        simples = r.regimes.get("simples")
        saida[f"fator_r_{nome}"] = float(simples.loc[meses, "fator_r"].iloc[-1]) if simples is not None else None
        saida[f"receita_{nome}"] = float(b.receita_bruta().loc[meses].sum())
    return saida
