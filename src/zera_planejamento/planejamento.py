"""Fluxo completo: base do cliente → histórico → cenários → equilíbrio → transição → sócios → prazos."""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

import pandas as pd

from .alertas import Alertas
from .base import BaseMensal
from .calculo import Resultado, calcular, simular_transicao
from .cliente import Cliente
from .equilibrio import curva_margem, margem_operacional, pontos_equilibrio
from .prazos import prazos
from .projecao import CENARIOS, Cenario, projetar
from .regras import pendencias_conferir
from .socios import VisaoSocios, visao_socios


@dataclass
class Planejamento:
    cliente: Cliente
    base: BaseMensal
    historico: Resultado
    meses_historico: pd.PeriodIndex
    cenarios: dict[str, Cenario]
    resumo: pd.DataFrame                 # cenário × regime
    equilibrio: pd.DataFrame
    curva: pd.DataFrame
    transicao: pd.DataFrame
    alertas: Alertas
    socios: VisaoSocios | None = None
    prazos: pd.DataFrame = field(default_factory=pd.DataFrame)
    gerado_em: dt.datetime = field(default_factory=dt.datetime.now)
    pendencias: list[str] = field(default_factory=pendencias_conferir)

    @property
    def meses_projetados(self) -> pd.PeriodIndex:
        return self.cenarios["Neutro"].meses

    def melhor(self, cenario: str = "Neutro") -> pd.Series | None:
        sub = self.resumo[(self.resumo["cenario"] == cenario) & self.resumo["melhor"]]
        return sub.iloc[0] if not sub.empty else None

    @property
    def margem_projetada(self) -> float:
        n = self.cenarios["Neutro"]
        return margem_operacional(n.base_completa, n.meses)


def gerar_planejamento(cliente: Cliente, base: BaseMensal, com_transicao: bool = True,
                       com_equilibrio: bool = True) -> Planejamento:
    """``com_equilibrio=False`` pula o break-even (o passo mais lento), útil no painel da carteira."""
    alertas = Alertas()
    rb = base.receita_bruta()
    com_receita = rb.index[rb > 0]
    if len(com_receita) == 0:
        raise ValueError("A base do cliente não tem receita. Importe os relatórios do Domínio primeiro.")
    hist_base = base.recorte(fim=com_receita.max())
    historico = calcular(hist_base, cliente, alertas)
    meses_hist = com_receita[-12:]
    cenarios = projetar(hist_base, cliente, alertas)

    linhas = []
    for nome in CENARIOS:
        r = cenarios[nome].resultado.resumo(cenarios[nome].meses).reset_index()
        r.insert(0, "cenario", nome)
        linhas.append(r)
    resumo = pd.concat(linhas, ignore_index=True)
    neutro = cenarios["Neutro"]
    for nome in CENARIOS:
        m = resumo[(resumo.cenario == nome) & resumo.melhor]
        if not m.empty and m.iloc[0]["economia_vs_2o"] < 0.03 * m.iloc[0]["tributos"]:
            alertas.atencao("Resultado", f"Cenário {nome}: vantagem do {m.iloc[0]['rotulo']} sobre o 2º colocado é "
                                         "menor que 3% — qualquer ajuste de premissa pode inverter a ordem.")
    socios = visao_socios(cliente, neutro.base_completa, neutro.resultado, neutro.meses)
    m = resumo[(resumo.cenario == "Neutro") & resumo.melhor]
    return Planejamento(
        cliente=cliente, base=base, historico=historico, meses_historico=meses_hist, cenarios=cenarios,
        resumo=resumo,
        equilibrio=pontos_equilibrio(neutro, cliente) if com_equilibrio else pd.DataFrame(),
        curva=curva_margem(neutro, cliente) if com_equilibrio else pd.DataFrame(),
        transicao=simular_transicao(hist_base, cliente) if com_transicao else pd.DataFrame(), alertas=alertas,
        socios=socios, prazos=prazos(cliente, m.iloc[0]["regime"] if not m.empty else None))
