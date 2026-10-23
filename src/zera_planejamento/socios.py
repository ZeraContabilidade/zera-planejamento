"""
Visão sócio + empresa (Lei 15.270/2025) e otimizador de pró-labore / Fator R.

Visão sócio + empresa
    Para cada regime, soma aos tributos da PJ o custo da retirada dos sócios no mesmo período:
    INSS (11%) e IRRF do pró-labore e o IRPFM dos lucros distribuídos. O IRRF de 10% sobre
    dividendos acima de R$ 50 mil/mês aparece à parte: é antecipação (caixa), abatida do IRPFM.

        lucro contábil = receita + rec. financeiras − custos − despesas − salários − pró-labore − FGTS
                         − (tributos do regime − CBS/IBS por fora)
        dividendos     = lucro contábil × fração distribuída × participação do sócio
        IRPFM          = regra de ``regras.pessoa_fisica.irpfm`` sobre a renda anualizada do sócio

Otimizador de pró-labore
    Testa valores de pró-labore mensal (total dos sócios) como se fossem pagos nos últimos 12 meses
    (regime estabilizado: a FS12 já reflete o novo valor) e devolve, por regime, o custo
    tributos da PJ + INSS + IRRF dos sócios. No Simples com Fator R mostra quando o Anexo III passa
    a valer. Não considera o efeito do pró-labore sobre os dividendos (ver visão sócio + empresa).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .alertas import Alertas
from .base import BaseMensal
from .calculo import ROTULO, Resultado, calcular
from .cliente import Cliente, Socio
from .formatos import brl
from .regras.pessoa_fisica import (DIVIDENDO_LIMITE_MES, SALARIO_MINIMO, inss_pro_labore, irpfm, irrf_dividendos,
                                   irrf_mensal, aliquota_efetiva_pj)
from .regras.simples import FATOR_R_CORTE, INICIO_RBT12_DEFASADA

POR_FORA = {"simples": [], "simples_hibrido": ["hibrido_cbs", "hibrido_ibs"], "presumido": ["cbs", "ibs"],
            "real": ["cbs", "ibs"]}


@dataclass
class VisaoSocios:
    resumo: pd.DataFrame            # uma linha por regime
    detalhe: pd.DataFrame           # regime × sócio
    observacoes: list[str] = field(default_factory=list)

    @property
    def vazia(self) -> bool:
        return self.resumo.empty


def _participacoes(socios: list[Socio]) -> list[float]:
    total = sum(max(s.participacao, 0.0) for s in socios)
    return [max(s.participacao, 0.0) / total if total > 0 else 1 / len(socios) for s in socios]


def custo_pro_labore(valor_mes: float, dependentes: int = 0) -> tuple[float, float]:
    """(INSS 11%, IRRF) do sócio sobre o pró-labore mensal."""
    inss = inss_pro_labore(valor_mes)
    return inss, irrf_mensal(valor_mes, inss, dependentes)


def lucro_contabil(regime: str, df: pd.DataFrame, dados: pd.DataFrame, cliente: Cliente) -> float | None:
    """Lucro do período depois dos tributos do regime (CBS/IBS por fora não reduzem o lucro)."""
    tem_dre = dados[["custos", "despesas"]].notna().any().any()
    tributos = float(df["total"].sum()) - sum(float(df[c].sum()) for c in POR_FORA[regime] if c in df)
    receita = float(df["receita"].sum())
    folha = float(dados[["salarios", "pro_labore", "fgts"]].fillna(0).to_numpy().sum())
    if tem_dre:
        custos = float(dados[["custos", "despesas"]].fillna(0).to_numpy().sum())
        fin = float(dados["receitas_financeiras"].fillna(0).sum())
        return receita + fin - custos - folha - tributos
    if cliente.lucro_anual_estimado is not None:
        return cliente.lucro_anual_estimado * len(df) / 12 - tributos
    return None


def visao_socios(cliente: Cliente, base: BaseMensal, resultado: Resultado, meses: pd.PeriodIndex) -> VisaoSocios:
    obs: list[str] = []
    if not cliente.socios:
        return VisaoSocios(pd.DataFrame(), pd.DataFrame(),
                           ["Cadastre os sócios (participação e pró-labore) para ver a carga sócio + empresa."])
    meses = base.dados.index.intersection(meses)
    n = len(meses)
    if n == 0:
        return VisaoSocios(pd.DataFrame(), pd.DataFrame(), ["Sem meses disponíveis para a visão dos sócios."])
    anualizar = 12 / n
    dados = base.dados.loc[base.dados.index.intersection(meses)]
    part = _participacoes(cliente.socios)
    pl_base = float(dados["pro_labore"].fillna(0).mean()) if len(dados) else 0.0
    resumo = resultado.resumo(meses)

    linhas, detalhe = [], []
    for regime, df in resultado.regimes.items():
        if not resumo.at[regime, "elegivel"]:
            continue
        df = df.loc[df.index.intersection(meses)]
        lucro = lucro_contabil(regime, df, dados, cliente)
        if lucro is None:
            obs.append(f"{ROTULO[regime]}: sem DRE e sem lucro estimado — dividendos não calculados.")
            continue
        irpj_csll = float(df[["irpj", "csll"]].sum().sum()) if {"irpj", "csll"} <= set(df.columns) else 0.0
        aliq_pj = aliquota_efetiva_pj(irpj_csll, lucro)
        dividendos = max(lucro, 0.0) * cliente.distribuicao_lucro
        tot = {"irrf_dividendos": 0.0, "irpfm": 0.0, "inss_socios": 0.0, "irrf_pro_labore": 0.0}
        for s, p in zip(cliente.socios, part):
            pl_mes = s.pro_labore if s.pro_labore is not None else pl_base * p
            inss, irrf_pl = custo_pro_labore(pl_mes, s.dependentes)
            div = dividendos * p
            if cliente.distribuicao_forma == "anual":
                irrf_div = irrf_dividendos(div)
            else:
                irrf_div = irrf_dividendos(div / n) * n
            renda_anual = (div + pl_mes * n) * anualizar + s.outros_rendimentos
            mp = irpfm(renda_anual, div * anualizar, irrf_pl * n * anualizar, aliq_pj)
            irpfm_periodo = mp["devido"] / anualizar
            detalhe.append({"regime": regime, "rotulo": ROTULO[regime], "socio": s.nome, "participacao": p,
                            "pro_labore_mes": pl_mes, "inss": inss * n, "irrf_pro_labore": irrf_pl * n,
                            "dividendos": div, "dividendos_mes": div / n, "irrf_dividendos": irrf_div,
                            "renda_anual": renda_anual, "aliquota_irpfm": mp["aliquota"],
                            "redutor": mp["redutor"] / anualizar, "irpfm": irpfm_periodo,
                            "ajuste_anual": irpfm_periodo - irrf_div})
            tot["irrf_dividendos"] += irrf_div
            tot["irpfm"] += irpfm_periodo
            tot["inss_socios"] += inss * n
            tot["irrf_pro_labore"] += irrf_pl * n
        tributos = float(resumo.at[regime, "tributos"])
        custo_pf = tot["irpfm"] + tot["inss_socios"] + tot["irrf_pro_labore"]
        linhas.append({"regime": regime, "rotulo": ROTULO[regime], "receita": float(resumo.at[regime, "receita"]),
                       "tributos_pj": tributos, "lucro_contabil": lucro, "aliquota_pj": aliq_pj,
                       "dividendos": dividendos, **tot, "custo_pf": custo_pf, "carga_total": tributos + custo_pf})
    res = pd.DataFrame(linhas)
    if res.empty:
        return VisaoSocios(res, pd.DataFrame(detalhe), obs)
    res = res.set_index("regime")
    res["carga_pct"] = res["carga_total"] / res["receita"]
    res["melhor"] = res["carga_total"] == res["carga_total"].min()
    det = pd.DataFrame(detalhe)

    if cliente.distribuicao_forma == "mensal" and (det["dividendos_mes"] > DIVIDENDO_LIMITE_MES).any():
        obs.append(f"Há sócio recebendo mais de {brl(DIVIDENDO_LIMITE_MES, 0)} por mês: retenção de 10% sobre o total "
                   "pago no mês. A retenção é antecipação do IRPFM; avalie o fluxo de caixa e a forma de distribuição, "
                   "sem fracionamento artificial.")
    if (det["aliquota_irpfm"] > 0).any():
        obs.append("Há sócio com renda anual acima de R$ 600 mil: IRPFM calculado com o redutor de 34% "
                   "[CONFERIR regulamentação].")
    melhor_pj = resumo[resumo["melhor"]].index
    melhor_total = res.index[res["melhor"]]
    if len(melhor_pj) and len(melhor_total) and melhor_pj[0] != melhor_total[0]:
        obs.append(f"Com a retirada dos sócios, a menor carga muda de {ROTULO[melhor_pj[0]]} para "
                   f"{ROTULO[melhor_total[0]]}.")
    if "simples" in res.index:
        obs.append("No Simples, a alíquota efetiva da PJ para o redutor do IRPFM foi considerada zero [CONFERIR].")
    return VisaoSocios(res, det, obs)


# --------------------------------------------------------------------------
@dataclass
class OtimizacaoProLabore:
    grade: pd.DataFrame             # pró-labore × custo por regime
    melhor: pd.DataFrame            # por regime: pró-labore ótimo, custo, economia
    atual: float
    para_fator_r: float | None      # pró-labore mensal que leva o Fator R a 28% (None sem receita Fator R)
    meses_ate_anexo_iii: int | None
    meses: pd.PeriodIndex


def otimizar_pro_labore(base: BaseMensal, cliente: Cliente, regimes=("simples", "presumido", "real"),
                        pontos: int = 21) -> OtimizacaoProLabore:
    rb = base.receita_bruta()
    com_receita = rb.index[rb > 0]
    if len(com_receita) == 0:
        raise ValueError("A base não tem receita: importe os relatórios antes de otimizar o pró-labore.")
    hist = base.recorte(fim=com_receita.max())
    meses = hist.meses[-12:]
    d = hist.dados.loc[meses]
    socios = cliente.socios or [Socio("Sócio")]
    part = _participacoes(socios)
    atual = float(d["pro_labore"].fillna(0).mean())
    rbt12 = float(rb.loc[meses].sum()) * 12 / len(meses)
    outros = float((d["salarios"].fillna(0) + d["fgts"].fillna(0)).mean())
    tem_fator_r = bool(d["rec_fator_r"].fillna(0).sum() > 0)
    para_fr = max(0.0, FATOR_R_CORTE * rbt12 / 12 - outros) if tem_fator_r else None

    minimo = SALARIO_MINIMO * len(socios)
    maximo = max(atual * 2, (para_fr or 0) * 1.3, minimo * 4)
    valores = set(np.round(np.linspace(minimo, maximo, pontos), 2)) | {round(max(atual, minimo), 2)}
    if para_fr:
        valores.add(round(max(math.ceil(para_fr * 100) / 100 + 0.01, minimo), 2))
    linhas = []
    for valor in sorted(valores):
        b = hist.copia()
        b.dados["pro_labore"] = valor
        r = calcular(b, cliente, Alertas(), regimes=list(regimes))
        resumo = r.resumo(meses)
        inss = irrf = 0.0
        for s, p in zip(socios, part):
            i, t = custo_pro_labore(valor * p, s.dependentes)
            inss, irrf = inss + i * len(meses), irrf + t * len(meses)
        linha = {"pro_labore": valor, "inss_socios": inss, "irrf_socios": irrf}
        if "simples" in r.regimes:
            linha["fator_r"] = float(r.regimes["simples"]["fator_r"].iloc[-1])
        for reg in r.regimes:
            if resumo.at[reg, "elegivel"]:
                linha[f"{reg}_pj"] = float(resumo.at[reg, "tributos"])
                linha[reg] = linha[f"{reg}_pj"] + inss + irrf
        linhas.append(linha)
    grade = pd.DataFrame(linhas)

    melhor = []
    ref = grade.iloc[(grade["pro_labore"] - max(atual, minimo)).abs().argmin()]
    for reg in regimes:
        if reg not in grade or grade[reg].isna().all():
            continue
        i = grade[reg].idxmin()
        melhor.append({"regime": reg, "rotulo": ROTULO[reg], "pro_labore": grade.at[i, "pro_labore"],
                       "custo": grade.at[i, reg], "custo_atual": ref.get(reg, np.nan),
                       "economia": ref.get(reg, np.nan) - grade.at[i, reg]})
    melhor = pd.DataFrame(melhor).set_index("regime") if melhor else pd.DataFrame()

    meses_iii = None
    if para_fr and "simples" in melhor.index:
        alvo = melhor.at["simples", "pro_labore"]
        if alvo > atual and ref.get("fator_r", 1.0) < FATOR_R_CORTE:
            fs12 = (outros + atual) * 12
            falta = FATOR_R_CORTE * rbt12 - fs12
            meses_iii = max(1, math.ceil(falta / (alvo - atual)))
            if meses.max() + 1 >= INICIO_RBT12_DEFASADA:
                meses_iii += 1          # 2027+: o mês anterior fica fora da FS12
    return OtimizacaoProLabore(grade, melhor, atual, para_fr, meses_iii, meses)
