"""
Reforma Tributária ano a ano (2026–2033) para o cliente — EC 132/2023 (ADCT, arts. 125 a 133) e LC 214/2025.

Os últimos 12 meses com receita do cliente são recalculados pelo motor com as regras de cada ano (mesma técnica de
``calculo.simular_transicao``: a série inteira é deslocada para que esses 12 meses caiam em jan–dez do ano, levando o
histórico junto para a RBT12). Aqui se guarda também a **composição** de cada regime (PIS/Cofins → CBS/IBS,
ICMS/ISS reduzidos de 2029 a 2032 e extintos em 2033), para mostrar onde a carga muda.

Premissas: operação e preço sem tributos iguais aos dos últimos 12 meses; CBS/IBS cobrados por fora; alíquotas de
referência estimadas (editáveis); Simples "por dentro" mantém o DAS e muda só a partilha.
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .alertas import Alertas
from .base import BaseMensal
from .calculo import COMPONENTES, NOME_TRIBUTO, REGIMES, calcular
from .cliente import Cliente
from .regras.reforma import RegrasReforma

ANOS = range(2026, 2034)
REGIME_DO_CADASTRO = {"simples": "simples", "presumido": "presumido", "real": "real"}

MARCOS = {
    2026: "Ano de teste: CBS 0,9% e IBS 0,1% destacados na nota e compensáveis — sem custo efetivo.",
    2027: "CBS plena; PIS e Cofins extintos; IPI zerado (exceto Zona Franca); Imposto Seletivo; IBS 0,1%. "
          "Simples pode optar pelo IBS/CBS por fora.",
    2028: "Mesmas regras de 2027 (CBS com redução de 0,1 p.p. e IBS 0,1%).",
    2029: "Começa a troca do ICMS/ISS pelo IBS: IBS a 10% da referência, ICMS/ISS a 90%.",
    2030: "IBS a 20% da referência; ICMS/ISS a 80%.",
    2031: "IBS a 30% da referência; ICMS/ISS a 70%.",
    2032: "IBS a 40% da referência; ICMS/ISS a 60%.",
    2033: "Modelo definitivo: IBS pleno; ICMS e ISS extintos.",
}


def cronograma(rr: RegrasReforma) -> pd.DataFrame:
    """Alíquotas e marcos de cada ano conforme as regras em uso (referências editáveis)."""
    return pd.DataFrame([{"ano": a, "cbs": rr.cbs(a), "ibs": rr.ibs(a), "icms_iss": rr.fator_icms_iss(a),
                          "pis_cofins": rr.pis_cofins_vigente(a), "marco": MARCOS[a]} for a in ANOS]).set_index("ano")


@dataclass
class ReformaCliente:
    anual: pd.DataFrame          # ano × regime (tributos no ano), + receita
    carga: pd.DataFrame          # ano × regime (carga sobre a receita)
    composicao: pd.DataFrame     # ano, regime, tributo, valor
    cronograma: pd.DataFrame
    melhor: pd.Series            # ano → regime de menor carga
    atual: str | None
    periodo_base: str            # ex.: "out/25 a set/26"
    observacoes: list[str] = field(default_factory=list)


def _cliente_com(cliente: Cliente, cbs: float | None, ibs: float | None, reducao: float | None) -> Cliente:
    reforma = dict(cliente.reforma)
    for k, v in (("cbs_referencia", cbs), ("ibs_referencia", ibs), ("reducao_aliquota", reducao)):
        if v is not None:
            reforma[k] = v
    return dataclasses.replace(cliente, reforma=reforma)


def simular_reforma(base: BaseMensal, cliente: Cliente, cbs: float | None = None, ibs: float | None = None,
                    reducao: float | None = None, anos=ANOS) -> ReformaCliente:
    """Mesmos 12 meses sob as regras de cada ano, com tributos e composição por regime."""
    cli = _cliente_com(cliente, cbs, ibs, reducao)
    rec = base.receita_bruta()
    com_receita = rec.index[rec > 0]
    if len(com_receita) == 0:
        raise ValueError("A base não tem receita: importe os relatórios antes de simular a Reforma.")
    ultimo = com_receita.max()
    meses_base = pd.period_range(ultimo - 11, ultimo, freq="M")
    from .formatos import comp
    linhas, cargas, comp_linhas = [], [], []
    for ano in anos:
        deslocamento = (ano * 12 + 11) - (ultimo.year * 12 + ultimo.month - 1)
        b = base.copia()
        b.dados.index = b.dados.index + deslocamento
        b.origem.index = b.dados.index
        res = calcular(b, cli, Alertas())
        r = res.resumo(pd.period_range(f"{ano}-01", f"{ano}-12", freq="M"))
        linha, carga = {"ano": ano, "receita": float(r["receita"].iloc[0])}, {"ano": ano}
        for reg in REGIMES:
            ok = reg in r.index and bool(r.at[reg, "elegivel"]) and not (reg == "simples_hibrido" and ano < 2027)
            linha[reg] = float(r.at[reg, "tributos"]) if ok else np.nan
            carga[reg] = float(r.at[reg, "carga"]) if ok else np.nan
            if ok:
                for k in COMPONENTES[reg]:
                    v = r.at[reg, f"comp_{k}"] if f"comp_{k}" in r.columns else np.nan
                    if pd.notna(v) and abs(v) > 0.005:
                        comp_linhas.append({"ano": ano, "regime": reg, "tributo": NOME_TRIBUTO[k], "valor": float(v)})
        linhas.append(linha)
        cargas.append(carga)
    anual = pd.DataFrame(linhas).set_index("ano")
    carga = pd.DataFrame(cargas).set_index("ano")
    regs = [r for r in REGIMES if anual[r].notna().any()]
    melhor = anual[regs].idxmin(axis=1)
    obs = []
    if cli.regras_reforma().reducao_aliquota:
        obs.append(f"Redução de {cli.regras_reforma().reducao_aliquota:.0%} do IBS/CBS sobre as vendas aplicada a "
                   "toda a receita (regime diferenciado) [CONFERIR enquadramento].".replace(".", ",", 0))
    obs.append("Simples “por dentro”: o DAS não muda com a Reforma (muda a partilha). O ganho do Simples híbrido para "
               "quem compra do cliente (crédito integral de IBS/CBS) não entra no cálculo do imposto do cliente.")
    return ReformaCliente(anual=anual[["receita"] + regs], carga=carga[regs], composicao=pd.DataFrame(comp_linhas),
                          cronograma=cronograma(cli.regras_reforma()), melhor=melhor,
                          atual=REGIME_DO_CADASTRO.get(cliente.regime_atual),
                          periodo_base=f"{comp(meses_base[0])} a {comp(meses_base[-1])}", observacoes=obs)


def indicadores(rf: ReformaCliente) -> dict:
    """Leitura rápida: menor carga hoje e em 2033, ano da virada, variação do regime atual e ganho de trocar."""
    a = rf.anual.drop(columns="receita")
    ind = {"melhor_2026": rf.melhor.get(2026), "melhor_2033": rf.melhor.get(2033)}
    mudancas = [ano for ano, ant in zip(rf.melhor.index[1:], rf.melhor.values[:-1]) if rf.melhor[ano] != ant]
    ind["anos_de_virada"] = mudancas
    if rf.atual in a.columns:
        ind["atual_2026"], ind["atual_2033"] = a.at[2026, rf.atual], a.at[2033, rf.atual]
        ind["variacao_atual"] = ind["atual_2033"] / ind["atual_2026"] - 1 if ind["atual_2026"] else np.nan
        melhor_por_ano = a.min(axis=1)
        ind["ganho_acumulado"] = float((a[rf.atual] - melhor_por_ano).loc[2027:2033].sum())
    variacao = (a.loc[2033] / a.loc[2026] - 1).dropna()
    if not variacao.empty:
        ind["mais_sobe"], ind["mais_sobe_var"] = variacao.idxmax(), float(variacao.max())
    return ind
