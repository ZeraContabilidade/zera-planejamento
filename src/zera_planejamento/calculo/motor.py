"""Orquestra os regimes sobre uma base mensal e resume os resultados."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from ..alertas import Alertas
from ..base import BaseMensal
from ..cliente import Cliente
from .comum import Contexto
from .presumido import calcular_presumido
from .real import calcular_real
from .simples import calcular_simples

REGIMES = ["simples", "simples_hibrido", "presumido", "real"]
ROTULO = {"simples": "Simples Nacional", "simples_hibrido": "Simples híbrido (IBS/CBS por fora)",
          "presumido": "Lucro Presumido", "real": "Lucro Real"}
COMPONENTES = {
    "simples": ["das", "cpp_fora_das", "icms_fora_das", "iss_fora_das"],
    "simples_hibrido": ["hibrido_das", "hibrido_cbs", "hibrido_ibs", "cpp_fora_das", "icms_fora_das", "iss_fora_das"],
    "presumido": ["pis", "cofins", "cbs", "ibs", "irpj", "csll", "icms", "iss", "encargos"],
    "real": ["pis", "cofins", "cbs", "ibs", "irpj", "csll", "icms", "iss", "encargos"],
}
NOME_TRIBUTO = {"das": "DAS", "cpp_fora_das": "CPP fora do DAS", "icms_fora_das": "ICMS fora do DAS",
                "iss_fora_das": "ISS fora do DAS", "hibrido_das": "DAS sem CBS/IBS", "hibrido_cbs": "CBS por fora",
                "hibrido_ibs": "IBS por fora", "pis": "PIS", "cofins": "Cofins", "cbs": "CBS", "ibs": "IBS",
                "irpj": "IRPJ", "csll": "CSLL", "icms": "ICMS", "iss": "ISS",
                "encargos": "INSS patronal + RAT + Terceiros"}


@dataclass
class Resultado:
    regimes: dict[str, pd.DataFrame]
    alertas: Alertas

    def mensal(self) -> pd.DataFrame:
        return pd.DataFrame({r: df["total"].where(df["elegivel"]) for r, df in self.regimes.items()})

    def resumo(self, meses: pd.PeriodIndex | None = None) -> pd.DataFrame:
        linhas = []
        for r, df in self.regimes.items():
            sub = df if meses is None else df.loc[df.index.intersection(meses)]
            valores = dict(zip(sub.columns, sub.to_numpy().T))
            receita = float(np.nansum(np.asarray(valores['receita'], dtype=float)))
            totais = np.asarray(valores['total'], dtype=float)
            total = float(totais.sum()) if not np.isnan(totais).any() else np.nan
            linhas.append({"regime": r, "rotulo": ROTULO[r], "receita": receita, "tributos": total,
                           "carga": total / receita if receita and not np.isnan(total) else np.nan,
                           "elegivel": not sub.empty and bool(valores['elegivel'].all()) and not np.isnan(total),
                           **{f"comp_{k}": float(np.nansum(np.asarray(valores[k], dtype=float)))
                              for k in COMPONENTES[r] if k in valores}})
        res = pd.DataFrame(linhas).set_index("regime")
        validos = res[res["elegivel"]].sort_values("tributos")
        res["melhor"] = False
        res["economia_vs_2o"] = 0.0
        if not validos.empty:
            res.loc[validos.index[0], "melhor"] = True
            if len(validos) > 1:
                res.loc[validos.index[0], "economia_vs_2o"] = validos["tributos"].iloc[1] - validos["tributos"].iloc[0]
        return res


def _hibrido(simples: pd.DataFrame) -> pd.DataFrame:
    """Simples com opção pelo IBS/CBS "por fora". Antes de 2027 a opção não existe: vale o DAS normal."""
    antes = simples.index.year < 2027
    valores = {k: simples[k].to_numpy() for k in COMPONENTES['simples_hibrido']}
    valores['hibrido_das'] = np.where(antes, simples['das'].to_numpy(), valores['hibrido_das'])
    for k in ('hibrido_cbs', 'hibrido_ibs'):
        valores[k] = np.where(antes, 0., valores[k])
    return pd.DataFrame({'receita': simples['receita'].to_numpy(), **valores,
                         'total': np.where(antes, simples['total'].to_numpy(), simples['hibrido_total'].to_numpy()),
                         'elegivel': simples['elegivel'].to_numpy() & (simples['hibrido_ok'].to_numpy() | antes)},
                        index=simples.index)


def calcular(base: BaseMensal, cliente: Cliente, alertas: Alertas | None = None,
             regimes: list[str] | None = None) -> Resultado:
    """Calcula os regimes pedidos (padrão: todos). O híbrido só aparece se houver mês ≥ 2027 calculável."""
    pedidos = regimes or REGIMES
    ctx = Contexto(base=base, cliente=cliente, alertas=alertas or Alertas(), memoria={})
    saida = {}
    if "simples" in pedidos or "simples_hibrido" in pedidos:
        simples = calcular_simples(ctx)
        if "simples" in pedidos:
            saida["simples"] = simples
        if "simples_hibrido" in pedidos and (simples["hibrido_ok"]).any():
            saida["simples_hibrido"] = _hibrido(simples)
    if "presumido" in pedidos:
        saida["presumido"] = calcular_presumido(ctx)
    if "real" in pedidos:
        saida["real"] = calcular_real(ctx)
    return Resultado(regimes=saida, alertas=ctx.alertas)


def simular_transicao(base: BaseMensal, cliente: Cliente, anos=range(2026, 2034)) -> pd.DataFrame:
    """Aplica as regras de cada ano aos últimos 12 meses da base.

    A série inteira é deslocada para que os últimos 12 meses com receita caiam em jan–dez do
    ano simulado (o histórico anterior vai junto, para a RBT12 sair certa).
    """
    rec = base.receita_bruta()
    com_receita = rec.index[rec > 0]
    if len(com_receita) == 0:
        return pd.DataFrame()
    ultimo = com_receita.max()
    linhas = []
    for ano in anos:
        deslocamento = (ano * 12 + 11) - (ultimo.year * 12 + ultimo.month - 1)
        b = base.copia()
        b.dados.index = b.dados.index + deslocamento
        b.origem.index = b.dados.index
        res = calcular(b, cliente, Alertas())
        meses = pd.period_range(f"{ano}-01", f"{ano}-12", freq="M")
        resumo = res.resumo(meses)
        linhas.append({"ano": ano, **{r: resumo.at[r, "tributos"] if r in resumo.index and resumo.at[r, "elegivel"]
                                      else np.nan for r in REGIMES},
                       "receita": resumo["receita"].iloc[0]})
    return pd.DataFrame(linhas).set_index("ano")
