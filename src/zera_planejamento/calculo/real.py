"""
Lucro Real.

- PIS 1,65% e Cofins 7,6% não cumulativos até 2026: débito sobre a receita (sem ICMS) menos
  crédito sobre aquisições (sem ICMS da compra), com saldo credor transportado. Receitas
  financeiras: 0,65% + 4% (Decreto 8.426/2015).
- A partir de 2027: CBS e IBS não cumulativos, com crédito amplo.
- Lucro antes do IRPJ/CSLL = receita + receitas financeiras − custos − despesas − salários −
  pró-labore − FGTS − encargos − PIS/Cofins − ICMS − ISS. CBS/IBS são "por fora" e não entram.
- Lucro real = lucro antes + adições − exclusões; IRPJ 15% + 10% (acima de R$ 20 mil × meses)
  e CSLL 9%, por trimestre ou anual, compensando prejuízo e base negativa de períodos
  anteriores até 30% do lucro do período.
- Sem custos/despesas na base: usa o ``lucro_anual_estimado`` do cadastro rateado pela receita;
  sem ele, o Lucro Real não é calculado.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..formatos import brl
from .comum import (Contexto, base_credito_iva, base_credito_pis_cofins, cbs_ibs, chave_periodo,
                    encargos_patronais, fator_icms_iss, nao_cumulativo, pis_cofins_vigente, ratear,
                    receita_liquida, tributos_locais)


def calcular_real(ctx: Contexto) -> pd.DataFrame:
    rf, idx, c = ctx.rf, ctx.d.index, ctx.cliente
    rl = receita_liquida(ctx)
    locais = tributos_locais(ctx)
    fator = fator_icms_iss(ctx)
    icms_deb, icms_cred, iss = locais["icms_debito"] * fator, locais["icms_credito"] * fator, locais["iss"] * fator
    vigente = pis_cofins_vigente(ctx)
    fin = ctx.col("receitas_financeiras")

    debito = (rl - (icms_deb if rf.excluir_icms_base_pis_cofins else 0)).clip(lower=0) * rf.pis_cofins_nao_cumulativo
    credito = base_credito_pis_cofins(ctx, locais) * rf.pis_cofins_nao_cumulativo
    pc, saldo_pc = nao_cumulativo(debito * vigente, credito * vigente)
    pc_fin = fin * rf.pis_cofins_receita_financeira * vigente
    part_pis = rf.pis_nao_cumulativo / rf.pis_cofins_nao_cumulativo
    iva = cbs_ibs(ctx, (rl - icms_deb - iss).clip(lower=0), base_credito_iva(ctx, locais))
    icms, _ = nao_cumulativo(icms_deb, icms_cred)
    enc = encargos_patronais(ctx)

    tem_resultado = ctx.d[["custos", "despesas"]].notna().any(axis=1)
    custos_desp = ctx.col("custos") + ctx.col("despesas")
    if not tem_resultado.any():
        if c.lucro_anual_estimado is None:
            ctx.alertas.atencao("Real", "Sem custos/despesas na base e sem lucro anual estimado no cadastro: "
                                        "o Lucro Real não foi calculado. Importe a DRE ou informe a estimativa.")
            return pd.DataFrame(index=idx).assign(receita=rl, total=np.nan, elegivel=False)
        ctx.alertas.atencao("Real", f"Sem DRE: Lucro Real calculado com o lucro anual estimado do cadastro "
                                    f"({brl(c.lucro_anual_estimado)}) rateado pela receita.")
        receita_12m = rl.tail(12).sum()
        margem = c.lucro_anual_estimado / receita_12m if receita_12m > 0 else 0.0
        lucro_antes = rl * margem   # margem = lucro estimado ÷ receita dos últimos 12 meses
    else:
        lucro_antes = (rl + fin - custos_desp - ctx.col("salarios") - ctx.col("pro_labore") - ctx.col("fgts")
                       - enc - pc - pc_fin - icms - iss)
    lucro = lucro_antes + ctx.col("adicoes") - ctx.col("exclusoes")

    periodo = chave_periodo(idx, anual=c.lr_periodo == "anual")
    irpj, csll = pd.Series(0.0, index=idx), pd.Series(0.0, index=idx)
    compensado, saldo_prej = pd.Series(0.0, index=idx), pd.Series(0.0, index=idx)
    prejuizo, base_neg = c.prejuizo_fiscal_inicial, c.base_negativa_inicial
    for _, meses in sorted(periodo.groupby(periodo).groups.items()):
        meses = pd.PeriodIndex(meses)
        n = len(meses)
        resultado = float(lucro[meses].sum())
        if resultado > 0:
            comp_ir = min(prejuizo, rf.trava_compensacao * resultado)
            comp_cs = min(base_neg, rf.trava_compensacao * resultado)
            prejuizo -= comp_ir
            base_neg -= comp_cs
            b_ir, b_cs = resultado - comp_ir, resultado - comp_cs
        else:
            comp_ir = 0.0
            prejuizo += -resultado
            base_neg += -resultado
            b_ir = b_cs = 0.0
        v_ir = rf.irpj * b_ir + rf.irpj_adicional * max(0.0, b_ir - rf.irpj_limite_adicional_mes * n)
        pesos = lucro[meses]
        irpj[meses] = ratear(v_ir, pesos)
        csll[meses] = ratear(rf.csll * b_cs, pesos)
        compensado[meses] = ratear(comp_ir, pesos)
        saldo_prej[meses] = prejuizo

    res = pd.DataFrame({
        "receita": rl, "lucro_antes_irpj": lucro_antes, "adicoes": ctx.col("adicoes"), "exclusoes": ctx.col("exclusoes"),
        "lucro_real": lucro, "prejuizo_compensado": compensado, "saldo_prejuizo": saldo_prej,
        "pis": (pc * part_pis) + fin * 0.0065 * vigente, "cofins": (pc * (1 - part_pis)) + fin * 0.04 * vigente,
        "saldo_credor_pis_cofins": saldo_pc, "cbs": iva["cbs"], "ibs": iva["ibs"], "irpj": irpj, "csll": csll,
        "icms": icms, "iss": iss, "encargos": enc,
    }, index=idx)
    res["total"] = res[["pis", "cofins", "cbs", "ibs", "irpj", "csll", "icms", "iss", "encargos"]].sum(axis=1)
    res["elegivel"] = True
    if prejuizo > 0:
        ctx.alertas.info("Real", f"Saldo de prejuízo fiscal ao fim do período: {brl(prejuizo)} (compensável até 30% "
                                 "do lucro dos períodos seguintes).")
    return res
