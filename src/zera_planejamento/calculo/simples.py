"""
Simples Nacional — DAS mês a mês ("por dentro") e, a partir de 2027, a opção híbrida.

Para cada período de apuração (PA):
1. RBT12 e FS12 pela janela da regra vigente no PA (``regras.simples.janela_rbt12``).
   Sem 12 meses na base: média dos meses disponíveis × 12 (Res. CGSN 140, art. 22) e alerta.
2. Fator R = FS12 / RBT12 decide III × V para a receita ``rec_fator_r``.
3. DAS = Σ receita do anexo × alíquota efetiva do anexo.
4. Sublimite de R$ 3,6 mi (art. 13-A e art. 20, §§ 1º e 1º-A): receita do ano anterior acima do
   sublimite, ou acumulada no ano (efeito no mês seguinte se o excesso passar de 20%; senão, em
   janeiro) → DAS sem o percentual de ICMS/ISS e ICMS/ISS apurados fora. RBT12 na 6ª faixa também
   leva ICMS/ISS para fora (a repartição dessa faixa não tem ICMS/ISS).
5. Anexo IV: CPP (20% + RAT×FAP) fora do DAS (art. 13, § 3º).
6. Elegibilidade pela receita do ano-calendário (art. 3º, §§ 9º e 9º-A).
7. Híbrido (≥ 2027, opção pelo regime regular de IBS/CBS): DAS sem a parcela de CBS/IBS da
   partilha + CBS/IBS não cumulativos "por fora" (dá crédito ao cliente PJ). Só calculado para
   os anexos com partilha em ``regras/dados/simples_partilha_reforma.csv``.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..formatos import brl
from ..regras.reforma import partilha_simples
from ..regras.simples import (FATOR_R_CORTE, ISS_EFETIVO_MAXIMO, LIMITE_EXCESSO, LIMITE_RECEITA,
                              SUBLIMITE_ICMS_ISS, aliquota_efetiva, janela_rbt12, percentual_icms_iss)
from .comum import (COLS_SERVICO, Contexto, base_credito_iva, cbs_ibs, encargos_patronais, nao_cumulativo,
                    receita_por_coluna, tributos_locais)

ANEXO_COLUNA = {"rec_anexo_i": "I", "rec_anexo_ii": "II", "rec_anexo_iii": "III", "rec_anexo_iv": "IV",
                "rec_anexo_v": "V"}


def _janela(serie: pd.Series, informado: pd.Series, pa: pd.Period) -> tuple[float, int]:
    ini, fim = janela_rbt12(pa)
    sel = (serie.index >= ini) & (serie.index <= fim) & informado.values
    return float(serie[sel].sum()), int(sel.sum())


def _parcela_icms_iss(pa: pd.Period, anexo: str, faixa: int, valor: float, aliq: float, rr_ativa: bool) -> float:
    """Valor de ICMS/ISS dentro do DAS da receita ``valor`` (sai do DAS quando a empresa está impedida)."""
    p = partilha_simples(pa.year, anexo, faixa) if rr_ativa else None
    if p is not None:
        icms, iss = p["icms"], p["iss"]
    else:
        share = percentual_icms_iss(anexo, faixa)
        icms, iss = (share, 0.0) if anexo in ("I", "II") else (0.0, share)
    return valor * (aliq * icms + min(aliq * iss, ISS_EFETIVO_MAXIMO))


def _impedimento_sublimite(rb: pd.Series, informado: pd.Series) -> tuple[pd.Series, bool]:
    """Meses impedidos de recolher ICMS/ISS no DAS (art. 20, §§ 1º e 1º-A) e se houve proporcionalização."""
    impedido = pd.Series(False, index=rb.index)
    rb_inf = rb[informado.values]
    por_ano = rb_inf.groupby(rb_inf.index.year).agg(["sum", "size"])
    proporcional, ano_corrente, acum, ano_anterior_acima, desde = False, None, 0.0, False, None
    for pa in rb.index:
        if pa.year != ano_corrente:
            ano_corrente, acum, desde, ano_anterior_acima = pa.year, 0.0, None, False
            if pa.year - 1 in por_ano.index:
                soma, n = por_ano.loc[pa.year - 1]
                proporcional |= n < 12
                # ano anterior acima do sublimite (proporcional aos meses informados): impedida o ano todo
                ano_anterior_acima = soma / n * 12 > SUBLIMITE_ICMS_ISS
        impedido[pa] = ano_anterior_acima or (desde is not None and pa >= desde)
        acum += rb[pa]
        # excesso acima de 20% no ano: efeito no mês seguinte; até 20%, só em janeiro (regra do ano anterior)
        if desde is None and acum > SUBLIMITE_ICMS_ISS * (1 + LIMITE_EXCESSO):
            desde = pa + 1
    return impedido, proporcional


def calcular_simples(ctx: Contexto) -> pd.DataFrame:
    d, c = ctx.d, ctx.cliente
    rec = receita_por_coluna(ctx)
    rb = rec.sum(axis=1)
    tem_receita = pd.Series(d[list(ANEXO_COLUNA) + ["rec_fator_r"]].notna().any(axis=1).values, index=d.index)
    folha = ctx.col("salarios") + ctx.col("pro_labore") + ctx.col("fgts")
    if c.fator_r_incluir_cpp:
        folha = folha + ctx.col("cpp_das")
    locais = tributos_locais(ctx)
    icms_rec, _ = nao_cumulativo(locais["icms_debito"], locais["icms_credito"])
    cpp_iv = encargos_patronais(ctx, terceiros=False)
    impedido, sub_proporcional = _impedimento_sublimite(rb, tem_receita)

    linhas, proporcional, sem_partilha = [], False, set()
    acum, ano_corrente, excluida_desde = 0.0, None, None
    for pa in d.index:
        soma_rb, n = _janela(rb, tem_receita, pa)
        soma_fs, _ = _janela(folha, tem_receita, pa)
        if n == 12:
            rbt12, fs12 = soma_rb, soma_fs
        elif n > 0:
            rbt12, fs12, proporcional = soma_rb / n * 12, soma_fs / n * 12, True
        else:
            rbt12, fs12, proporcional = rb[pa] * 12, folha[pa] * 12, True
        fator_r = fs12 / rbt12 if rbt12 > 0 else 0.0
        anexo_fr = "III" if fator_r >= FATOR_R_CORTE else "V"

        fora = bool(impedido[pa]) or rbt12 > SUBLIMITE_ICMS_ISS
        das, das_cbs, das_ibs, faixa_max, aliqs, hibrido_ok = 0.0, 0.0, 0.0, 1, {}, True
        excluido = 0.0
        for col in rec.columns:
            anexo = ANEXO_COLUNA.get(col, anexo_fr)
            aliq, faixa = aliquota_efetiva(rbt12, anexo)
            aliqs[col] = aliq
            valor = rec.at[pa, col]
            if valor <= 0:
                continue
            faixa_max = max(faixa_max, faixa)
            das_col = valor * aliq
            if fora:          # impedida: o DAS sai sem a parcela de ICMS/ISS
                parcela = _parcela_icms_iss(pa, anexo, faixa, valor, aliq, ctx.rr.ativa)
                excluido += parcela
                das -= parcela
            das += das_col
            if pa.year >= 2027 and ctx.rr.ativa:
                p = partilha_simples(pa.year, anexo, faixa)
                if p is None:
                    hibrido_ok = False
                    sem_partilha.add(anexo)
                else:
                    das_cbs += das_col * p["cbs"]
                    das_ibs += das_col * p["ibs"]

        icms_fora = float(icms_rec[pa]) if fora else 0.0
        iss_fora = float(locais.at[pa, "iss"]) if fora else 0.0
        cpp_fora = float(cpp_iv[pa]) if rec.at[pa, "rec_anexo_iv"] > 0 else 0.0

        if pa.year != ano_corrente:
            ano_corrente, acum = pa.year, 0.0
        elegivel = excluida_desde is None or pa < excluida_desde
        acum += rb[pa]
        if acum > LIMITE_RECEITA * (1 + LIMITE_EXCESSO) and (excluida_desde is None or excluida_desde > pa + 1):
            excluida_desde = pa + 1          # excesso > 20%: exclusão no mês seguinte
        elif excluida_desde is None and acum > LIMITE_RECEITA:
            excluida_desde = pd.Period(year=pa.year + 1, month=1, freq="M")

        linhas.append({"competencia": pa, "receita": rb[pa], "rbt12": rbt12, "fs12": fs12, "fator_r": fator_r,
                       "anexo_fator_r": anexo_fr, "faixa": faixa_max,
                       **{f"aliq_{k}": v for k, v in aliqs.items()},
                       "das": das, "das_icms_iss_excluido": excluido, "das_cbs": das_cbs, "das_ibs": das_ibs, "cpp_fora_das": cpp_fora,
                       "icms_fora_das": icms_fora, "iss_fora_das": iss_fora,
                       "total": das + cpp_fora + icms_fora + iss_fora, "elegivel": bool(elegivel),
                       "hibrido_ok": hibrido_ok and pa.year >= 2027 and ctx.rr.ativa})
    res = pd.DataFrame(linhas).set_index("competencia")

    # ---- híbrido: DAS sem CBS/IBS + CBS/IBS por fora (base = receita da operação) ----
    iva = cbs_ibs(ctx, rb, base_credito_iva(ctx, locais))
    res["hibrido_das"] = res["das"] - res["das_cbs"] - res["das_ibs"]
    res["hibrido_cbs"], res["hibrido_ibs"] = iva["cbs"], iva["ibs"]
    res["hibrido_total"] = np.where(res["hibrido_ok"], res["hibrido_das"] + iva["cbs"] + iva["ibs"]
                                    + res["cpp_fora_das"] + res["icms_fora_das"] + res["iss_fora_das"], np.nan)

    al = ctx.alertas
    if proporcional:
        al.info("Simples", "RBT12/FS12 proporcionalizados (média × 12) nos meses sem 12 meses anteriores na base. "
                           "Inclua o histórico (Domínio desde janeiro do ano anterior ou digitado) para precisão.")
    if (~res["elegivel"]).any():
        meses = ", ".join(str(p) for p in res.index[~res["elegivel"]])
        al.critico("Simples", f"Receita do ano acima de {brl(LIMITE_RECEITA, 0)}: exclusão do Simples "
                              f"(LC 123, art. 3º, §§ 9º e 9º-A). Fora da comparação em {meses}.")
    if (res["rbt12"] > SUBLIMITE_ICMS_ISS).any():
        al.atencao("Simples", "RBT12 na 6ª faixa (acima de R$ 3,6 mi): ICMS/ISS fora do DAS. Se a empresa ainda não "
                              "estiver impedida pelo sublimite, conferir a regra da Res. CGSN 140/2018, art. 25.")
    if impedido.any():
        meses = ", ".join(str(p) for p in impedido.index[impedido])
        al.atencao("Simples", f"Sublimite de {brl(SUBLIMITE_ICMS_ISS, 0)} ultrapassado (LC 123, art. 20, §§ 1º e 1º-A): "
                              f"DAS sem ICMS/ISS e ICMS/ISS apurados fora em {meses}.")
    if sub_proporcional and impedido.any():
        al.info("Simples", "Sublimite do ano anterior avaliado pela média dos meses informados × 12.")
    if sem_partilha:
        al.atencao("Simples", f"Sem tabela de partilha CBS/IBS para o(s) anexo(s) {', '.join(sorted(sem_partilha))}: "
                              "o Simples híbrido não foi calculado nesses meses.")
    if (rec[COLS_SERVICO].sum(axis=1) > 0).any() and (rec["rec_fator_r"] > 0).any():
        al.info("Simples", "Receita com Fator R: o anexo (III ou V) muda conforme a folha dos 12 meses.")
    return res
