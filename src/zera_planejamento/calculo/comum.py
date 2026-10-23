"""Peças comuns aos regimes: receita, ICMS/ISS, encargos, não cumulatividade, CBS/IBS, trimestres."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from ..alertas import Alertas
from ..base import CREDITO_PIS_COFINS, CREDITO_SO_CBS, RECEITAS, BaseMensal
from ..cliente import Cliente
from ..formatos import pct
from ..regras.federais import RegrasFederais
from ..regras.reforma import RegrasReforma

COLS_MERCADORIA = ["rec_anexo_i", "rec_anexo_ii"]
COLS_SERVICO = ["rec_anexo_iii", "rec_anexo_iv", "rec_anexo_v", "rec_fator_r"]


@dataclass
class Contexto:
    base: BaseMensal
    cliente: Cliente
    rf: RegrasFederais = field(default=None)
    rr: RegrasReforma = field(default=None)
    alertas: Alertas = field(default_factory=Alertas)

    def __post_init__(self):
        self.rf = self.rf or self.cliente.regras_federais()
        self.rr = self.rr or self.cliente.regras_reforma()

    @property
    def d(self) -> pd.DataFrame:
        return self.base.dados

    def col(self, nome: str) -> pd.Series:
        return self.d[nome].fillna(0.0)

    def anos(self) -> np.ndarray:
        return np.asarray(self.d.index.year)


# --------------------------------------------------------------------------
def receita_por_coluna(ctx: Contexto) -> pd.DataFrame:
    """Receita de cada anexo já sem devoluções (rateio proporcional)."""
    rec = ctx.d[RECEITAS].fillna(0.0)
    total = rec.sum(axis=1).replace(0, np.nan)
    fator = (1 - ctx.col("devolucoes") / total).clip(lower=0).fillna(1.0)
    return rec.mul(fator, axis=0)


def receita_liquida(ctx: Contexto) -> pd.Series:
    return receita_por_coluna(ctx).sum(axis=1)


def tributos_locais(ctx: Contexto) -> pd.DataFrame:
    """ICMS (débito/crédito) e ISS como seriam fora do Simples.

    Cliente hoje no Simples: os relatórios não trazem ICMS/ISS próprios (estão no DAS), então
    o motor estima pelas alíquotas do cadastro. Fora do Simples: usa o informado e estima só
    os meses vazios.
    """
    c, rec = ctx.cliente, receita_por_coluna(ctx)
    est_deb = rec[COLS_MERCADORIA].sum(axis=1) * c.icms_aliquota_saida
    est_cred = ctx.col("cred_insumos") * c.icms_aliquota_entrada * (rec[COLS_MERCADORIA].sum(axis=1) > 0)
    est_iss = rec[COLS_SERVICO].sum(axis=1) * c.iss_aliquota
    if c.regime_atual == "simples":
        deb, cred, iss = est_deb, est_cred, est_iss
        if (est_deb > 0).any() or (est_iss > 0).any():
            ctx.alertas.info("Cálculo", "Cliente no Simples: ICMS e ISS do Presumido/Real estimados pelas alíquotas "
                                        f"do cadastro (ISS {pct(c.iss_aliquota)}, ICMS saída "
                                        f"{pct(c.icms_aliquota_saida)}).")
    else:
        deb = ctx.d["icms_debito"].fillna(est_deb)
        cred = ctx.d["icms_credito"].fillna(est_cred)
        iss = ctx.d["iss"].fillna(est_iss)
    return pd.DataFrame({"icms_debito": deb, "icms_credito": cred, "iss": iss}, index=ctx.d.index)


def nao_cumulativo(debito: pd.Series, credito: pd.Series, saldo_inicial: float = 0.0) -> tuple[pd.Series, pd.Series]:
    """Débito − crédito mês a mês com transporte do saldo credor. (a recolher, saldo credor)."""
    saldo, pagar, saldos = saldo_inicial, [], []
    for d, c in zip(debito.fillna(0), credito.fillna(0)):
        liquido = d - c - saldo
        if liquido >= 0:
            pagar.append(liquido)
            saldo = 0.0
        else:
            pagar.append(0.0)
            saldo = -liquido
        saldos.append(saldo)
    return pd.Series(pagar, index=debito.index), pd.Series(saldos, index=debito.index)


def encargos_patronais(ctx: Contexto, terceiros: bool = True) -> pd.Series:
    """INSS 20% sobre salários e pró-labore + RAT×FAP (+ Terceiros) sobre salários."""
    c, sal, pl = ctx.cliente, ctx.col("salarios"), ctx.col("pro_labore")
    total = ctx.rf.cpp * (sal + pl) + c.rat * c.fap * sal
    return total + (c.terceiros * sal if terceiros else 0.0)


def base_credito_pis_cofins(ctx: Contexto, locais: pd.DataFrame) -> pd.Series:
    """Aquisições com crédito de PIS/Cofins, sem o ICMS da compra (Lei 14.592/2023)."""
    base = ctx.d[CREDITO_PIS_COFINS].fillna(0).sum(axis=1) - locais["icms_credito"]
    return base.clip(lower=0)


def base_credito_iva(ctx: Contexto, locais: pd.DataFrame) -> pd.Series:
    """Crédito amplo de CBS/IBS (LC 214, art. 47): inclui uso e consumo e, se marcado, imobilizado."""
    base = base_credito_pis_cofins(ctx, locais) + ctx.d[CREDITO_SO_CBS].fillna(0).sum(axis=1)
    if ctx.rr.credito_imobilizado:
        base = base + ctx.col("imobilizado")
    return base


def cbs_ibs(ctx: Contexto, base_debito: pd.Series, base_credito: pd.Series) -> pd.DataFrame:
    """CBS e IBS não cumulativos, com a alíquota do ano de cada competência."""
    anos = ctx.anos()
    a_cbs = pd.Series([ctx.rr.cbs(a) for a in anos], index=ctx.d.index)
    a_ibs = pd.Series([ctx.rr.ibs(a) for a in anos], index=ctx.d.index)
    cbs, _ = nao_cumulativo(base_debito * a_cbs, base_credito * a_cbs)
    ibs, _ = nao_cumulativo(base_debito * a_ibs, base_credito * a_ibs)
    return pd.DataFrame({"cbs": cbs, "ibs": ibs, "aliq_cbs": a_cbs, "aliq_ibs": a_ibs}, index=ctx.d.index)


def fator_icms_iss(ctx: Contexto) -> pd.Series:
    return pd.Series([ctx.rr.fator_icms_iss(a) for a in ctx.anos()], index=ctx.d.index)


def pis_cofins_vigente(ctx: Contexto) -> pd.Series:
    return pd.Series([ctx.rr.pis_cofins_vigente(a) for a in ctx.anos()], index=ctx.d.index)


def chave_periodo(index: pd.PeriodIndex, anual: bool = False) -> pd.Series:
    """AAAAT (ex. 20263 = 3º tri/2026) ou AAAA."""
    return pd.Series([p.year if anual else p.year * 10 + p.quarter for p in index], index=index)


def ratear(valor: float, pesos: pd.Series) -> pd.Series:
    pesos = pesos.clip(lower=0)
    if pesos.sum() <= 0:
        return pd.Series(valor / len(pesos), index=pesos.index)
    return valor * pesos / pesos.sum()
