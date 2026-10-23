"""
Pontos de equilíbrio (break-even) sobre o cenário Neutro.

1. Lucro Real × Presumido e Lucro Real × Simples — margem operacional em que custam o mesmo.
   Margem operacional = (receita líquida − custos − despesas) ÷ receita, antes de folha, tributos
   e encargos. Abaixo do equilíbrio o Real é mais barato.
2. Simples × Presumido — faturamento médio mensal em que se igualam (receita e itens variáveis
   escalados juntos; folha e despesas fixas mantidas).
3. Fator R — folha necessária para os serviços sujeitos ao Fator R irem do Anexo V ao III e a
   economia de DAS no período.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from functools import lru_cache

from .alertas import Alertas
from .base import RECEITAS, BaseMensal
from .calculo import calcular
from .calculo.comum import Contexto, chave_periodo
from .calculo.real import apurar_lucro
from .cliente import Cliente
from .formatos import brl, pct
from .projecao import VARIAVEIS, Cenario
from .regras.simples import FATOR_R_CORTE, aliquota_efetiva


def _custo(regime: str, base: BaseMensal, cliente: Cliente, meses: pd.PeriodIndex) -> float:
    res = calcular(base, cliente, Alertas(), regimes=[regime]).regimes.get(regime)
    if res is None:
        return float("inf")
    sub = res.loc[meses]
    if not sub["elegivel"].all() or sub["total"].isna().any():
        return float("inf")
    return float(sub["total"].sum())


def margem_operacional(base: BaseMensal, meses: pd.PeriodIndex) -> float:
    d = base.dados.loc[meses]
    rl = base.receita_bruta().loc[meses].sum()
    if rl <= 0:
        return float("nan")
    return float((rl - d["custos"].fillna(0).sum() - d["despesas"].fillna(0).sum()) / rl)


def _com_margem(base: BaseMensal, meses: pd.PeriodIndex, m: float) -> BaseMensal:
    b = base.copia()
    d = b.dados
    rl = b.receita_bruta().loc[meses]
    alvo = rl.sum() * (1 - m) - d.loc[meses, "custos"].fillna(0).sum()
    atual = d.loc[meses, "despesas"].fillna(0)
    d.loc[meses, "despesas"] = (atual * alvo / atual.sum()) if atual.sum() > 0 else alvo * rl / rl.sum()
    return b


def _avaliador_margem(base: BaseMensal, cliente: Cliente, meses: pd.PeriodIndex):
    """Prepara os componentes invariantes e reutiliza a apuração oficial do Lucro Real."""
    original = calcular(base, cliente, regimes=['real']).regimes['real']
    if 'lucro_real' not in original or not original.loc[meses, 'elegivel'].all():
        return lambda margem: float('inf')
    ctx = Contexto(base, cliente)
    periodo = chave_periodo(base.meses, anual=cliente.lr_periodo == 'anual')
    grupos = sorted(periodo.groupby(periodo).indices.items())
    pos = base.meses.get_indexer(meses)
    lucro_original = original['lucro_real'].to_numpy()
    # Mesma ordem de soma de calcular_real; evita subtrair tributos de um total arredondado.
    fixos = original[['pis', 'cofins', 'cbs', 'ibs', 'icms', 'iss', 'encargos']].to_numpy()
    receitas = base.receita_bruta().loc[meses].to_numpy()
    soma_receitas = receitas.sum()
    custos = base.dados.loc[meses, 'custos'].fillna(0).sum()
    despesas = base.dados.loc[meses, 'despesas'].fillna(0).to_numpy()
    soma_despesas = despesas.sum()

    def avaliar(margem):
        alvo = soma_receitas * (1 - margem) - custos
        if soma_despesas > 0:
            novas = despesas * alvo / soma_despesas
        elif soma_receitas > 0:
            novas = alvo * receitas / soma_receitas
        else:
            return float('inf')
        lucro = lucro_original.copy()
        lucro[pos] += despesas - novas
        irpj, csll, _, _, _ = apurar_lucro(ctx, lucro, grupos)
        parcelas = np.column_stack((fixos[:, :4], irpj, csll, fixos[:, 4:]))
        return float(np.nansum(parcelas, axis=1)[pos].sum())
    return avaliar


def _escalar(base: BaseMensal, meses: pd.PeriodIndex, k: float) -> BaseMensal:
    b = base.copia()
    cols = RECEITAS + VARIAVEIS
    b.dados.loc[meses, cols] = b.dados.loc[meses, cols] * k
    return b


def _raizes(f, lo: float, hi: float, passos: int = 12, iteracoes: int = 18) -> list[float]:
    """Raízes de f em [lo, hi]: grade + bissecção (precisão ~ (hi−lo)/passos/2^iteracoes)."""
    grade = np.linspace(lo, hi, passos)
    vals = [f(x) for x in grade]
    out = []
    for (x0, v0), (x1, v1) in zip(zip(grade, vals), zip(grade[1:], vals[1:])):
        if not all(np.isfinite(v) for v in (v0, v1)) or np.sign(v0) == np.sign(v1):
            continue
        a, b, fa = x0, x1, v0
        for _ in range(iteracoes):
            mid = (a + b) / 2
            fm = f(mid)
            if not np.isfinite(fm):
                break
            if np.sign(fm) == np.sign(fa):
                a, fa = mid, fm
            else:
                b = mid
        else:
            out.append((a + b) / 2)
    return out


def pontos_equilibrio(neutro: Cenario, cliente: Cliente) -> pd.DataFrame:
    base, meses = neutro.base_completa, neutro.meses
    m_atual = margem_operacional(base, meses)
    rl = base.receita_bruta().loc[meses]
    m_max = 1 - base.dados.loc[meses, "custos"].fillna(0).sum() / rl.sum() - 0.001 if rl.sum() else 0.5
    linhas = []
    tem_resultado = base.dados.loc[meses, ["custos", "despesas"]].notna().any().any()
    # Cache restrito a esta chamada: ambas as comparações percorrem a mesma grade.
    custo_real = lru_cache(maxsize=256)(_avaliador_margem(base, cliente, meses)) if tem_resultado else None

    for outro, nome in (("presumido", "Lucro Presumido"), ("simples", "Simples Nacional")):
        if not tem_resultado:
            break
        fixo = _custo(outro, base, cliente, meses)

        def f(m):
            v = custo_real(m)
            return np.nan if np.isinf(v) or np.isinf(fixo) else v - fixo

        r = _raizes(f, -0.30, m_max)
        if r:
            m_eq = min(r, key=lambda x: abs(x - m_atual))
            lado = "Lucro Real" if m_atual < m_eq else nome
            leitura = (f"Com margem abaixo de {pct(m_eq, 1)} o Lucro Real fica mais barato que o {nome}. "
                       f"Margem projetada: {pct(m_atual, 1)} — favorece o {lado}.")
        else:
            m_eq, leitura = np.nan, "Sem cruzamento entre −30% e a margem máxima possível."
        linhas.append({"comparacao": f"Lucro Real × {nome}", "indicador": "Margem operacional", "unidade": "%",
                       "equilibrio": m_eq, "projetado": m_atual, "leitura": leitura})

    def g(k):
        b = _escalar(base, meses, k)
        a, c = _custo("simples", b, cliente, meses), _custo("presumido", b, cliente, meses)
        if not np.isfinite(a) or not np.isfinite(c):
            return np.nan
        return float(np.clip(a - c, -1e15, 1e15))

    fat = float(rl.mean())
    r = _raizes(g, 0.2, 4.0, 16)
    if r:
        k = min(r, key=lambda x: abs(x - 1))
        abaixo = g(k * 0.9) < 0
        leitura = (f"Simples e Presumido se igualam com faturamento médio de {brl(fat * k, 0)}/mês "
                   f"({pct(k, 0)} do projetado). {'Abaixo' if abaixo else 'Acima'} disso o Simples é mais barato.")
        eq = fat * k
    else:
        diferenca = g(1.0)
        if np.isnan(diferenca) and all(not np.isfinite(_custo(reg, base, cliente, meses))
                                      for reg in ('simples', 'presumido')):
            eq, leitura = np.nan, 'Simples e Presumido indisponíveis no período: sem comparação de faturamento.'
        else:
            lado = "Simples" if diferenca < 0 else "Presumido"
            eq, leitura = np.nan, f"Sem cruzamento entre 20% e 400% do faturamento projetado: {lado} continua mais barato."
    linhas.append({"comparacao": "Simples × Lucro Presumido", "indicador": "Faturamento médio mensal", "unidade": "R$",
                   "equilibrio": eq, "projetado": fat, "leitura": leitura})

    simples = neutro.resultado.regimes["simples"].loc[meses]
    rec_fr = base.dados.loc[meses, "rec_fator_r"].fillna(0)
    if rec_fr.sum() > 0:
        fr, rbt12, fs12 = simples["fator_r"].iloc[0], simples["rbt12"].iloc[0], simples["fs12"].iloc[0]
        falta = max(0.0, FATOR_R_CORTE * rbt12 - fs12)
        economia = sum(rec_fr[p] * (simples.at[p, "aliq_rec_fator_r"] - aliquota_efetiva(simples.at[p, "rbt12"], "III")[0])
                       for p in meses if simples.at[p, "anexo_fator_r"] == "V")
        if falta > 0 and economia > 0:
            leitura = (f"Fator R de {pct(fr, 1)}: faltam {brl(falta, 0)} de folha em 12 meses (~{brl(falta / 12, 0)}/mês) "
                       f"para o Anexo III. Economia de DAS no período: {brl(economia, 0)}. Compare com o INSS (11% do "
                       "sócio + 20% patronal fora do Simples) e o IRPF sobre o pró-labore adicional.")
        elif falta > 0:
            leitura = f"Fator R de {pct(fr, 1)}: nesta RBT12 o Anexo V não é mais caro que o III; não compensa aumentar a folha."
        else:
            leitura = f"Fator R de {pct(fr, 1)}, acima de 28%: serviços no Anexo III. Mantenha a folha."
        linhas.append({"comparacao": "Simples — Fator R (Anexo III × V)", "indicador": "Fator R", "unidade": "%",
                       "equilibrio": FATOR_R_CORTE, "projetado": fr, "leitura": leitura})
    return pd.DataFrame(linhas)


def curva_margem(neutro: Cenario, cliente: Cliente, pontos: int = 18) -> pd.DataFrame:
    base, meses = neutro.base_completa, neutro.meses
    rl = base.receita_bruta().loc[meses].sum()
    if rl <= 0 or not base.dados.loc[meses, ["custos", "despesas"]].notna().any().any():
        return pd.DataFrame()
    hi = min(0.6, 1 - base.dados.loc[meses, "custos"].fillna(0).sum() / rl - 0.001)
    fixos = {r: _custo(r, base, cliente, meses) for r in ("simples", "presumido")}
    custo_real = _avaliador_margem(base, cliente, meses)
    linhas = []
    for m in np.linspace(-0.1, hi, pontos):
        linhas.append({"margem": m, **fixos, "real": custo_real(m)})
    return pd.DataFrame(linhas).replace(np.inf, np.nan)
