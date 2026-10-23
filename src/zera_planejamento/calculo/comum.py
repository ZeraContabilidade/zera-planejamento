"""Peças comuns aos regimes: receita, ICMS/ISS, encargos, não cumulatividade, CBS/IBS, trimestres."""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import wraps

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
    memoria: dict | None = field(default=None, repr=False)

    def __post_init__(self):
        self.rf = self.rf or self.cliente.regras_federais()
        self.rr = self.rr or self.cliente.regras_reforma()

    @property
    def d(self) -> pd.DataFrame:
        return self.base.dados

    def col(self, nome: str) -> pd.Series:
        if self.memoria is not None:
            chave = ('col', nome)
            if chave not in self.memoria:
                self.memoria[chave] = self.d[nome].fillna(0.0)
            return self.memoria[chave]
        return self.d[nome].fillna(0.0)

    def anos(self) -> np.ndarray:
        return np.asarray(self.d.index.year)

    def vetor(self, nome: str) -> np.ndarray:
        if self.memoria is not None:
            chave = ('vetor', nome)
            if chave not in self.memoria:
                if 'colunas' not in self.memoria:
                    self.memoria['colunas'] = dict(zip(self.d.columns, self.d.to_numpy().T))
                bruto = self.memoria['colunas'][nome]
                self.memoria[chave] = np.where(np.isnan(bruto), 0., bruto)
            return self.memoria[chave]
        return self.col(nome).to_numpy()

    def soma_colunas(self, nomes: list[str]) -> np.ndarray:
        """Soma por linha com a mesma semântica de NaN do pandas."""
        chave = ('soma', tuple(nomes))
        if self.memoria is not None and chave in self.memoria:
            return self.memoria[chave]
        valores = np.column_stack([self.vetor(nome) for nome in nomes]).sum(axis=1)
        if self.memoria is not None:
            self.memoria[chave] = valores
        return valores


# --------------------------------------------------------------------------
def _por_calculo(funcao):
    """Reaproveita somente no Contexto privado de uma chamada de calcular.

    Contextos públicos continuam sem cache, pois sua base pode ser editada pelo chamador.
    Os consumidores internos não alteram os objetos retornados.
    """
    @wraps(funcao)
    def executar(ctx, *args, **kwargs):
        if ctx.memoria is None:
            return funcao(ctx, *args, **kwargs)
        chave = (funcao.__name__, args, tuple(sorted(kwargs.items())))
        if chave not in ctx.memoria:
            ctx.memoria[chave] = funcao(ctx, *args, **kwargs)
        return ctx.memoria[chave]
    return executar


@_por_calculo
def receita_por_coluna(ctx: Contexto) -> pd.DataFrame:
    """Receita de cada anexo já sem devoluções (rateio proporcional)."""
    valores = ctx.d[RECEITAS].to_numpy()
    rec = np.where(np.isnan(valores), 0.0, valores)
    total = rec.sum(axis=1)
    fator = np.ones(len(total))
    np.divide(ctx.col('devolucoes').to_numpy(), total, out=fator, where=total != 0)
    fator = np.where(total != 0, np.maximum(1 - fator, 0), 1.0)
    return pd.DataFrame(rec * fator[:, None], index=ctx.d.index, columns=RECEITAS)


def receita_liquida(ctx: Contexto) -> pd.Series:
    return receita_por_coluna(ctx).sum(axis=1)


@_por_calculo
def tributos_locais(ctx: Contexto) -> pd.DataFrame:
    """ICMS (débito/crédito) e ISS como seriam fora do Simples.

    Cliente hoje no Simples: os relatórios não trazem ICMS/ISS próprios (estão no DAS), então
    o motor estima pelas alíquotas do cadastro. Fora do Simples: usa o informado e estima só
    os meses vazios.
    """
    c, rec = ctx.cliente, receita_por_coluna(ctx)
    valores = rec.to_numpy()
    mercadoria = valores[:, rec.columns.get_indexer(COLS_MERCADORIA)].sum(axis=1)
    est_deb = mercadoria * c.icms_aliquota_saida
    est_cred = ctx.vetor("cred_insumos") * c.icms_aliquota_entrada * (mercadoria > 0)
    est_iss = valores[:, rec.columns.get_indexer(COLS_SERVICO)].sum(axis=1) * c.iss_aliquota
    if c.regime_atual == "simples":
        deb, cred, iss = est_deb, est_cred, est_iss
        if (est_deb > 0).any() or (est_iss > 0).any():
            ctx.alertas.info("Cálculo", "Cliente no Simples: ICMS e ISS do Presumido/Real estimados pelas alíquotas "
                                        f"do cadastro (ISS {pct(c.iss_aliquota)}, ICMS saída "
                                        f"{pct(c.icms_aliquota_saida)}).")
    else:
        def informado_ou_estimado(nome, estimado):
            valores = ctx.d[nome].to_numpy()
            return np.where(np.isnan(valores), estimado, valores)
        deb = informado_ou_estimado('icms_debito', est_deb)
        cred = informado_ou_estimado('icms_credito', est_cred)
        iss = informado_ou_estimado('iss', est_iss)
    return pd.DataFrame({"icms_debito": deb, "icms_credito": cred, "iss": iss}, index=ctx.d.index)


def nao_cumulativo(debito: pd.Series, credito: pd.Series, saldo_inicial: float = 0.0) -> tuple[pd.Series, pd.Series]:
    """Débito − crédito mês a mês com transporte do saldo credor. (a recolher, saldo credor)."""
    pagar, saldos = _nao_cumulativo_array(debito.to_numpy(), credito.to_numpy(), saldo_inicial)
    return pd.Series(pagar, index=debito.index), pd.Series(saldos, index=debito.index)


def _nao_cumulativo_array(debito, credito, saldo_inicial=0.0):
    saldo, pagar, saldos = saldo_inicial, [], []
    for d, c in zip(np.where(np.isnan(debito), 0, debito), np.where(np.isnan(credito), 0, credito)):
        liquido = d - c - saldo
        if liquido >= 0:
            pagar.append(liquido)
            saldo = 0.0
        else:
            pagar.append(0.0)
            saldo = -liquido
        saldos.append(saldo)
    return np.asarray(pagar), np.asarray(saldos)


@_por_calculo
def encargos_patronais(ctx: Contexto, terceiros: bool = True) -> pd.Series:
    """INSS 20% sobre salários e pró-labore + RAT×FAP (+ Terceiros) sobre salários."""
    c, sal, pl = ctx.cliente, ctx.vetor("salarios"), ctx.vetor("pro_labore")
    total = ctx.rf.cpp * (sal + pl) + c.rat * c.fap * sal
    return pd.Series(total + (c.terceiros * sal if terceiros else 0.0), index=ctx.d.index)


def base_credito_pis_cofins(ctx: Contexto, locais: pd.DataFrame) -> pd.Series:
    """Aquisições com crédito de PIS/Cofins, sem o ICMS da compra (Lei 14.592/2023)."""
    base = ctx.soma_colunas(CREDITO_PIS_COFINS) - locais['icms_credito'].to_numpy()
    return pd.Series(np.maximum(base, 0), index=ctx.d.index)


def base_credito_iva(ctx: Contexto, locais: pd.DataFrame) -> pd.Series:
    """Crédito amplo de CBS/IBS (LC 214, art. 47): inclui uso e consumo e, se marcado, imobilizado."""
    base = base_credito_pis_cofins(ctx, locais).to_numpy() + ctx.soma_colunas(CREDITO_SO_CBS)
    if ctx.rr.credito_imobilizado:
        base = base + ctx.col("imobilizado").to_numpy()
    return pd.Series(base, index=ctx.d.index)


def cbs_ibs(ctx: Contexto, base_debito: pd.Series, base_credito: pd.Series) -> pd.DataFrame:
    """CBS e IBS não cumulativos, com a alíquota do ano de cada competência."""
    anos = ctx.anos()
    a_cbs = np.array([ctx.rr.cbs(a) for a in anos])
    a_ibs = np.array([ctx.rr.ibs(a) for a in anos])
    debito, credito = np.asarray(base_debito), np.asarray(base_credito)
    cbs, _ = _nao_cumulativo_array(debito * a_cbs, credito * a_cbs)
    ibs, _ = _nao_cumulativo_array(debito * a_ibs, credito * a_ibs)
    return pd.DataFrame({"cbs": cbs, "ibs": ibs, "aliq_cbs": a_cbs, "aliq_ibs": a_ibs}, index=ctx.d.index)


@_por_calculo
def fator_icms_iss(ctx: Contexto) -> pd.Series:
    return pd.Series([ctx.rr.fator_icms_iss(a) for a in ctx.anos()], index=ctx.d.index)


@_por_calculo
def pis_cofins_vigente(ctx: Contexto) -> pd.Series:
    return pd.Series([ctx.rr.pis_cofins_vigente(a) for a in ctx.anos()], index=ctx.d.index)


def chave_periodo(index: pd.PeriodIndex, anual: bool = False) -> pd.Series:
    """AAAAT (ex. 20263 = 3º tri/2026) ou AAAA."""
    return pd.Series([p.year if anual else p.year * 10 + p.quarter for p in index], index=index)


def ratear(valor: float, pesos: pd.Series) -> pd.Series:
    return pd.Series(ratear_array(valor, pesos.to_numpy()), index=pesos.index)


def ratear_array(valor: float, pesos: np.ndarray) -> np.ndarray:
    """Mesmo rateio, sem construir Series intermediárias nos laços dos períodos."""
    positivos = np.maximum(pesos, 0)
    soma = np.nansum(positivos)
    if soma <= 0:
        return np.full(len(pesos), valor / len(pesos))
    return valor * positivos / soma
