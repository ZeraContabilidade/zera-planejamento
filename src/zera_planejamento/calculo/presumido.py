"""
Lucro Presumido.

- PIS 0,65% e Cofins 3% cumulativos (até 2026), sem ICMS na base (Tema 69).
- A partir de 2027: CBS e IBS não cumulativos, com crédito amplo (LC 214/2025).
- IRPJ e CSLL por trimestre, rateados aos meses pela base presumida:
      base = Σ receita do anexo × presunção + acréscimo LC 224/2025 + receitas financeiras
      IRPJ = 15% × base + 10% × (base − R$ 20 mil × meses do trimestre);  CSLL = 9% × base
- LC 224/2025: +10% no percentual de presunção sobre a receita que exceder R$ 1,25 mi no
  trimestre, com aproveitamento do saldo não usado e ajuste no 4º trimestre ao limite anual
  de R$ 5 mi (IN RFB 2.306/2026, art. 15), rateado pela participação de cada atividade.
- ICMS e ISS (reduzidos de 2029 a 2032 e extintos em 2033) e encargos sobre a folha.
"""
from __future__ import annotations

import pandas as pd

from .comum import (Contexto, base_credito_iva, cbs_ibs, chave_periodo, encargos_patronais, fator_icms_iss,
                    nao_cumulativo, pis_cofins_vigente, ratear, receita_por_coluna, tributos_locais)


def excesso_lc224(rec_tri: pd.Series, meses_tri: pd.Series, inicio: pd.Period, ctx: Contexto) -> pd.Series:
    """Receita sujeita ao acréscimo por trimestre (índice AAAAT)."""
    rf = ctx.rf
    excesso = pd.Series(0.0, index=rec_tri.index)
    if not rf.lc224_ativo:
        return excesso
    for ano in sorted({k // 10 for k in rec_tri.index}):
        saldo = anteriores = lim_total = rec_total = 0.0
        for k in sorted(k for k in rec_tri.index if k // 10 == ano):
            if pd.Period(year=ano, month=3 * (k % 10) - 2, freq="M") < inicio:
                continue
            rec, n = rec_tri[k], meses_tri[k]
            limite = rf.lc224_limite_trimestral * n / 3
            disponivel = limite + saldo
            exc = max(0.0, rec - disponivel)
            saldo = max(0.0, disponivel - rec)
            lim_total += limite
            rec_total += rec
            if k % 10 == 4 and n == 3:   # ajuste anual (§ 5º)
                exc = max(0.0, rec_total - lim_total) - anteriores
            excesso[k] = exc
            anteriores += exc
    return excesso


def calcular_presumido(ctx: Contexto) -> pd.DataFrame:
    rf, idx = ctx.rf, ctx.d.index
    rec = receita_por_coluna(ctx)
    rl = rec.sum(axis=1)
    locais = tributos_locais(ctx)
    fator = fator_icms_iss(ctx)
    icms_deb = locais["icms_debito"] * fator
    icms_cred = locais["icms_credito"] * fator
    iss = locais["iss"] * fator
    vigente = pis_cofins_vigente(ctx)

    base_pc = (rl - (icms_deb if rf.excluir_icms_base_pis_cofins else 0)).clip(lower=0)
    pis = base_pc * rf.pis_cumulativo * vigente
    cofins = base_pc * rf.cofins_cumulativo * vigente
    iva = cbs_ibs(ctx, (rl - icms_deb - iss).clip(lower=0), base_credito_iva(ctx, locais))

    pres_irpj = pd.Series({c: rf.presuncao[c][0] for c in rec.columns})
    pres_csll = pd.Series({c: rf.presuncao[c][1] for c in rec.columns})
    fin = ctx.col("receitas_financeiras")
    base_irpj_mes = rec.mul(pres_irpj, axis=1).sum(axis=1) + fin
    base_csll_mes = rec.mul(pres_csll, axis=1).sum(axis=1) + fin

    tri = chave_periodo(idx)
    rec_tri, meses_tri = rl.groupby(tri).sum(), rl.groupby(tri).size()
    exc_irpj = excesso_lc224(rec_tri, meses_tri, pd.Period(rf.lc224_inicio_irpj, "M"), ctx)
    exc_csll = excesso_lc224(rec_tri, meses_tri, pd.Period(rf.lc224_inicio_csll, "M"), ctx)

    irpj, csll = pd.Series(0.0, index=idx), pd.Series(0.0, index=idx)
    acr_irpj, acr_csll = pd.Series(0.0, index=idx), pd.Series(0.0, index=idx)
    for k, meses in tri.groupby(tri).groups.items():
        meses = pd.PeriodIndex(meses)
        n = len(meses)
        rq = rec.loc[meses].sum()
        part = rq / rq.sum() if rq.sum() > 0 else rq * 0
        extra_irpj = exc_irpj[k] * float((part * pres_irpj).sum()) * rf.lc224_acrescimo
        extra_csll = exc_csll[k] * float((part * pres_csll).sum()) * rf.lc224_acrescimo
        b_irpj = max(0.0, base_irpj_mes[meses].sum() + extra_irpj)
        b_csll = max(0.0, base_csll_mes[meses].sum() + extra_csll)
        v_irpj = rf.irpj * b_irpj + rf.irpj_adicional * max(0.0, b_irpj - rf.irpj_limite_adicional_mes * n)
        irpj[meses] = ratear(v_irpj, base_irpj_mes[meses])
        csll[meses] = ratear(rf.csll * b_csll, base_csll_mes[meses])
        acr_irpj[meses] = ratear(extra_irpj, base_irpj_mes[meses])
        acr_csll[meses] = ratear(extra_csll, base_csll_mes[meses])

    icms, _ = nao_cumulativo(icms_deb, icms_cred)
    res = pd.DataFrame({
        "receita": rl, "base_presumida_irpj": base_irpj_mes + acr_irpj, "base_presumida_csll": base_csll_mes + acr_csll,
        "acrescimo_lc224_irpj": acr_irpj, "acrescimo_lc224_csll": acr_csll,
        "pis": pis, "cofins": cofins, "cbs": iva["cbs"], "ibs": iva["ibs"], "irpj": irpj, "csll": csll,
        "icms": icms, "iss": iss, "encargos": encargos_patronais(ctx),
    }, index=idx)
    res["total"] = res[["pis", "cofins", "cbs", "ibs", "irpj", "csll", "icms", "iss", "encargos"]].sum(axis=1)

    anual = rl.groupby(idx.year).sum()
    res["elegivel"] = True
    for ano, valor in anual.items():
        if valor > rf.limite_lucro_presumido:
            res.loc[idx.year > ano, "elegivel"] = False
            ctx.alertas.critico("Presumido", f"Receita de {ano} acima de R$ 78 mi: Lucro Real obrigatório a partir de "
                                             f"{ano + 1} (Lei 9.718/98, art. 13).")
    if (acr_irpj + acr_csll).sum() > 0:
        ctx.alertas.info("Presumido", "Acréscimo de presunção da LC 224/2025 aplicado (receita acima de R$ 1,25 mi no "
                                      "trimestre / R$ 5 mi no ano). Tema com questionamento judicial.")
    return res
