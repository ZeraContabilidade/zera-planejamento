"""
Importação dos relatórios do Domínio para a base mensal do cliente.

| Relatório          | Colunas da base                                           | Mês              |
|--------------------|-----------------------------------------------------------|------------------|
| Serviços / Saídas  | rec_anexo_* (por acumulador ou CFOP)                      | data da nota     |
| Entradas           | cred_*, uso_consumo, imobilizado, devolucoes (por CFOP)   | data de entrada  |
| Extrato da folha   | salarios, pro_labore (base INSS), fgts                    | competência      |
| DRE                | custos, despesas, receitas_financeiras, adicoes, exclusoes| período da DRE   |

Só os meses cobertos pelo período de cada relatório são regravados; nesses meses, as colunas
alimentadas pelo relatório recebem zero quando não há movimento (para não sobrar valor antigo).
"""
from __future__ import annotations

import datetime as dt
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from ..alertas import Alertas
from ..base import COLUNAS, RECEITAS, BaseMensal
from ..cliente import Cliente
from ..formatos import brl, comp
from .depara import DESTINOS, DePara
from .leitura import normalizar
from .relatorios import Relatorio, ler_relatorio

# Zeradas nos meses cobertos. Aluguel fica de fora: em geral não tem nota com CFOP e é digitado.
COLS_ENTRADAS = ["cred_insumos", "cred_energia", "cred_servicos", "cred_fretes", "uso_consumo", "imobilizado",
                 "devolucoes"]
COLS_FOLHA = ["salarios", "pro_labore", "fgts"]
COLS_DRE_SEMPRE = ["custos", "despesas", "receitas_financeiras"]


def _colunas(destino: str) -> list[str]:
    if destino == "despesa_indedutivel":
        return ["despesas", "adicoes"]
    return [destino] if destino in COLUNAS else []


@dataclass
class Importacao:
    relatorios: list[Relatorio]
    parciais: dict[str, pd.DataFrame] = field(default_factory=dict)
    alertas: Alertas = field(default_factory=Alertas)
    entradas_cfop: pd.DataFrame | None = None
    dre_contas: pd.DataFrame | None = None
    folha_resumo: pd.DataFrame | None = None
    receita_mensal: pd.Series | None = None
    cruzadas: list[dict] = field(default_factory=list)

    def aplicar(self, base: BaseMensal, quando: str | None = None) -> int:
        quando = quando or f"{dt.datetime.now():%d/%m/%Y %H:%M}"
        n = 0
        for tipo, parcial in self.parciais.items():
            arquivos = ", ".join(r.arquivo for r in self.relatorios if r.tipo in _TIPOS_DA_PARCIAL[tipo])
            n += len(base.mesclar(parcial, f"Domínio {tipo} ({arquivos}) {quando}"))
        return n


_TIPOS_DA_PARCIAL = {"receita": ("servicos", "saidas"), "entradas": ("entradas",), "folha": ("folha",),
                     "dre": ("dre",)}


class _Acumulador:
    def __init__(self):
        self.valores = defaultdict(float)     # (periodo, coluna) -> valor
        self.colunas: set[str] = set()
        self.meses: set[pd.Period] = set()

    def somar(self, per: pd.Period, coluna: str, valor: float) -> None:
        self.valores[(per, coluna)] += valor
        self.colunas.add(coluna)

    def cobrir(self, meses) -> None:
        self.meses.update(meses)

    def df(self, sempre: list[str]) -> pd.DataFrame | None:
        if not self.meses:
            return None
        cols = sorted(self.colunas | set(sempre), key=list(COLUNAS).index)
        idx = pd.PeriodIndex(sorted(self.meses), freq="M", name="competencia")
        out = pd.DataFrame(0.0, index=idx, columns=cols)
        for (per, col), v in self.valores.items():
            if per in out.index:
                out.at[per, col] += v
        return out.round(2)


# --------------------------------------------------------------------------
def importar_relatorios(arquivos: list[str | Path], cliente: Cliente, base_atual: BaseMensal | None = None) -> Importacao:
    relatorios = [ler_relatorio(a) for a in arquivos]
    imp = Importacao(relatorios=relatorios)
    dp = DePara.do_cliente(cliente)
    al = imp.alertas
    for r in dp.invalidas:
        al.atencao("De-Para", f"Regra inválida ignorada: {r.tipo} '{r.chave}' → '{r.destino}'.")
    por_tipo = defaultdict(list)
    for r in relatorios:
        por_tipo[r.tipo].append(r)

    # identificação da empresa
    cnpj_cli = "".join(ch for ch in cliente.cnpj if ch.isdigit())
    raizes = {r.cnpj[:8] for r in relatorios if r.cnpj}
    if len(raizes) > 1:
        al.critico("Importação", f"Relatórios de empresas diferentes (raízes de CNPJ {', '.join(sorted(raizes))}).")
    if cnpj_cli and raizes and cnpj_cli[:8] not in raizes:
        al.critico("Importação", f"CNPJ dos relatórios ({', '.join(sorted(raizes))}) não é o do cliente "
                                 f"({cliente.cnpj}).")

    folha = None
    if por_tipo["folha"]:
        folha = por_tipo["folha"][0]
        if len(por_tipo["folha"]) > 1:
            folha.dados = pd.concat([r.dados for r in por_tipo["folha"]], ignore_index=True)
            folha.inicio = min(r.inicio for r in por_tipo["folha"])
            folha.fim = max(r.fim for r in por_tipo["folha"])

    _receita(imp, por_tipo["servicos"] + por_tipo["saidas"], dp, cliente)
    if por_tipo["entradas"]:
        _entradas(imp, por_tipo["entradas"], dp, folha, cliente)
    if folha is not None:
        _folha(imp, folha, dp)
    if por_tipo["dre"]:
        _dre(imp, por_tipo["dre"], dp, folha, base_atual)
    return imp


# --------------------------------------------------------------------------
def _receita(imp: Importacao, rels: list[Relatorio], dp: DePara, cliente: Cliente) -> None:
    if not rels:
        return
    acc, al, total = _Acumulador(), imp.alertas, pd.Series(dtype=float)
    sempre = set()
    for rel in rels:
        df = rel.dados.copy()
        acc.cobrir(rel.meses)
        sempre.update([dp.coluna_servico] if rel.tipo == "servicos" else ["rec_anexo_i", "rec_anexo_ii"])
        if df.empty:
            continue
        if rel.tipo == "servicos":
            df["destino"] = df["acumulador"].map(dp.acumulador)
        else:
            df["destino"] = df["cfop"].map(lambda c: dp.cfop("CFOP_SAIDA", c)[0])
            for destino, g in df[~df["destino"].isin(RECEITAS)].groupby("destino"):
                nivel = "ATENÇÃO" if destino == "NAO_CLASSIFICADO" else "INFO"
                al.add(nivel, "Saídas", f"{len(g)} nota(s), {brl(g.valor.sum())}, com destino "
                                        f"'{DESTINOS.get(destino, destino)}' (CFOP {', '.join(sorted(g.cfop.unique()))}).")
            st = df[df["cfop"].str[1:].isin(["403", "405"])]
            if not st.empty:
                al.atencao("Saídas", f"Vendas com ST (x403/x405) de {brl(st.valor.sum())}: no Simples a parte do ICMS "
                                     "sai do DAS — o sistema não segrega.")
        for _, n in df.iterrows():
            if n["destino"] in RECEITAS:
                acc.somar(n["competencia"], n["destino"], n["valor"])
        if cliente.regime_atual != "simples":
            col_imp = "imp_iss" if rel.tipo == "servicos" else "imp_icms"
            destino_imp = "iss" if rel.tipo == "servicos" else "icms_debito"
            if col_imp in df:
                for per, v in df.groupby("competencia")[col_imp].sum().items():
                    acc.somar(per, destino_imp, v)
        receita = df[df["destino"].isin(RECEITAS)]
        total = total.add(receita.groupby("competencia")["valor"].sum(), fill_value=0)
        dup = df[df.duplicated(["nota", "serie", "participante", "valor"], keep=False)]
        if not dup.empty:
            al.atencao(rel.arquivo, f"Notas repetidas: {', '.join(dup.nota.unique()[:10])}.")
        impresso = rel.extras.get("total_geral")
        if impresso is not None and abs(impresso - df.valor.sum()) > 0.05:
            al.critico(rel.arquivo, f"Soma lida {brl(df.valor.sum())} ≠ Total Geral impresso {brl(impresso)}: "
                                    "o layout do relatório pode ter mudado.")
    imp.parciais["receita"] = acc.df(sorted(sempre))
    imp.receita_mensal = total


def _entradas(imp: Importacao, rels: list[Relatorio], dp: DePara, folha: Relatorio | None, cliente: Cliente) -> None:
    acc, al, frames = _Acumulador(), imp.alertas, []
    for rel in rels:
        acc.cobrir(rel.meses)
        df = rel.dados.copy()
        if df.empty:
            continue
        regra = df.apply(lambda n: dp.cfop("CFOP_ENTRADA", n["cfop"], n["participante"]), axis=1)
        df["destino"], df["regra"] = [r[0] for r in regra], [r[1] for r in regra]
        frames.append(df)
        impresso = rel.extras.get("total_geral")
        if impresso is not None and abs(impresso - df.valor.sum()) > 0.05:
            al.critico(rel.arquivo, f"Soma lida {brl(df.valor.sum())} ≠ Total Geral impresso {brl(impresso)}.")
    if not frames:
        imp.parciais["entradas"] = acc.df(COLS_ENTRADAS)
        return
    df = pd.concat(frames, ignore_index=True)
    for _, n in df.iterrows():
        for col in _colunas(n["destino"]):
            acc.somar(n["competencia"], col, n["valor"])
    if cliente.regime_atual != "simples" and "imp_icms" in df:
        for per, v in df[df.destino.str.startswith("cred_")].groupby("competencia")["imp_icms"].sum().items():
            acc.somar(per, "icms_credito", v)
    imp.parciais["entradas"] = acc.df(COLS_ENTRADAS)
    imp.entradas_cfop = (df.groupby(["cfop", "destino", "regra"]).agg(notas=("valor", "size"), valor=("valor", "sum"))
                         .reset_index().sort_values("cfop"))
    imp.entradas_cfop["destino_txt"] = imp.entradas_cfop["destino"].map(lambda d: DESTINOS.get(d, d))

    def tot(destino):
        return df.loc[df.destino == destino, "valor"].sum()

    if tot("NAO_CLASSIFICADO"):
        cf = ", ".join(sorted(df.loc[df.destino == "NAO_CLASSIFICADO", "cfop"].unique()))
        al.atencao("Entradas", f"CFOP sem regra ({cf}): {brl(tot('NAO_CLASSIFICADO'))} ficou fora. Inclua a regra no De-Para.")
    if tot("imobilizado"):
        al.info("Entradas", f"Imobilizado de {brl(tot('imobilizado'))}: sem crédito de PIS/Cofins na aquisição (só pela "
                            "depreciação, não modelada); crédito integral de CBS/IBS a partir de 2027.")
    if tot("uso_consumo"):
        al.info("Entradas", f"Uso e consumo/comunicação de {brl(tot('uso_consumo'))}: sem crédito de PIS/Cofins, com "
                            "crédito de CBS/IBS a partir de 2027.")
    ign = df[df.destino == "IGNORAR"].groupby("cfop")["valor"].sum()
    if not ign.empty:
        al.info("Entradas", "Fora da base por não serem compra: " + "; ".join(f"CFOP {c} {brl(v)}" for c, v in ign.items()) + ".")
    difal = df.filter(like="imp_difal").sum().sum()
    if difal:
        al.info("Entradas", f"DIFAL de {brl(difal)} no período (custo do Simples, não modelado).")
    # prestadores pessoa física/MEI e ex-empregados
    cpfs = {}
    if folha is not None:
        for _, p in folha.dados.drop_duplicates("cpf").iterrows():
            dem = folha.dados.loc[folha.dados.cpf == p.cpf, "demissao"].dropna()
            cpfs[p.cpf] = (p.nome, dem.iloc[0] if not dem.empty else None)
    for participante, g in df[df.cfop.str[1:] == "933"].groupby("participante"):
        m = re.search(r"(\d{8}|\d{11})\s*$", participante)
        if not m:
            continue
        datas = ", ".join(f"{d:%d/%m/%Y}" for d in sorted(g["data"]))
        if m[1] in cpfs:
            nome, dem = cpfs[m[1]]
            quando = f", demitido em {dem:%d/%m/%Y}" if dem else ""
            al.atencao("Entradas", f"Serviço tomado de {participante} ({len(g)} nota(s), {brl(g.valor.sum())}, em {datas}): "
                                   f"CPF igual ao do empregado {nome}{quando}. Risco de vínculo empregatício e de "
                                   "contribuição previdenciária — conferir contrato e natureza do serviço.")
        else:
            al.info("Entradas", f"Serviço tomado de MEI/pessoa física ({participante}, {len(g)} nota(s), "
                                f"{brl(g.valor.sum())}): o crédito pode não existir ou ser limitado.")
    dup = df[df.duplicated(["nota", "serie", "participante", "cfop", "valor"], keep=False)]
    if not dup.empty:
        al.atencao("Entradas", f"Notas repetidas (mesma nota, CFOP e valor): {', '.join(dup.nota.unique()[:10])}.")


def _folha(imp: Importacao, rel: Relatorio, dp: DePara) -> None:
    acc, df = _Acumulador(), rel.dados.copy()
    df["destino"] = df.apply(lambda p: dp.vinculo(p["vinculo"], p["categoria"]), axis=1)
    acc.cobrir(df.competencia.unique())
    for _, p in df.iterrows():
        for col in _colunas(p["destino"]):
            acc.somar(p["competencia"], col, p["base_inss"])
        acc.somar(p["competencia"], "fgts", p["fgts"])
    imp.parciais["folha"] = acc.df(COLS_FOLHA)
    imp.folha_resumo = (df.assign(empregados=np.where(df.destino == "salarios", df.base_inss, 0.0),
                                  pro_labore=np.where(df.destino == "pro_labore", df.base_inss, 0.0))
                        .groupby("competencia").agg(empregados=("empregados", "sum"), pro_labore=("pro_labore", "sum"),
                                                    fgts=("fgts", "sum"), proventos=("proventos", "sum"),
                                                    pessoas=("nome", "nunique")).reset_index())
    for c, impresso in rel.extras.get("total_proventos", {}).items():
        lido = df.loc[df.competencia.astype(str) == c, "proventos"].sum()
        if abs(lido - impresso) > 0.05:
            imp.alertas.critico("Folha", f"{c}: proventos lidos {brl(lido)} ≠ total impresso {brl(impresso)}.")
    ign = df[df.destino == "IGNORAR"]
    if not ign.empty:
        imp.alertas.info("Folha", f"{ign.nome.nunique()} pessoa(s) com vínculo ignorado ({', '.join(ign.vinculo.unique())}).")


def _segmentos_dre(rels: list[Relatorio]):
    """DREs acumuladas do mesmo exercício viram períodos por diferença."""
    rels, anterior, segmentos = sorted(rels, key=lambda r: r.fim), None, []
    for rel in rels:
        chave = ["classificacao", "descricao", "codigo"]
        contas = rel.dados.set_index(chave)["saldo"]
        if rel.extras.get("acumulada_desde_janeiro") and anterior is not None and anterior.fim.year == rel.fim.year:
            delta = contas.subtract(anterior.dados.set_index(chave)["saldo"], fill_value=0)
            inicio = pd.Period(anterior.fim, "M") + 1
        else:
            delta, inicio = contas, pd.Period(rel.inicio, "M")
        segmentos.append((rel, list(pd.period_range(inicio, pd.Period(rel.fim, "M"), freq="M")), delta.reset_index()))
        anterior = rel
    return segmentos


def _dre(imp: Importacao, rels: list[Relatorio], dp: DePara, folha: Relatorio | None, base_atual: BaseMensal | None) -> None:
    acc, al, todas = _Acumulador(), imp.alertas, []
    for rel, meses, contas in _segmentos_dre(rels):
        acc.cobrir(meses)
        regra = contas.apply(lambda c: dp.conta_dre(c["codigo"], c["classificacao"], c["descricao"]), axis=1)
        contas["destino"], contas["regra"] = [r[0] for r in regra], [r[1] for r in regra]
        if folha is None:   # sem extrato: contas de pessoal da DRE alimentam a folha
            def sem_folha(c):
                if c["destino"] != "FOLHA":
                    return c["destino"]
                d = normalizar(c["descricao"])
                return "pro_labore" if "labore" in d else ("fgts" if "fgts" in d else "salarios")
            contas["destino"] = contas.apply(sem_folha, axis=1)
        n = len(meses)
        for _, c in contas.iterrows():
            for col in _colunas(c["destino"]):
                valor = c["saldo"] if col in ("receitas_financeiras", "exclusoes") or col in RECEITAS else -c["saldo"]
                for p in meses:
                    acc.somar(p, col, valor / n)
        contas["periodo"] = f"{comp(meses[0])} a {comp(meses[-1])}"
        todas.append(contas)
        if n > 1:
            al.atencao("DRE", f"DRE de {comp(meses[0])} a {comp(meses[-1])} veio acumulada: custos, despesas e receitas "
                              f"financeiras foram divididos igualmente pelos {n} meses. Como o IRPJ/CSLL do Lucro Real é "
                              "trimestral, exporte a DRE de cada mês para o resultado por trimestre ficar exato.")
        impresso, soma = rel.extras.get("resultado_impresso"), rel.dados["saldo"].sum()
        if impresso is not None and abs(impresso - soma) > 0.05:
            al.critico(rel.arquivo, f"Soma das contas {brl(soma)} ≠ resultado impresso {brl(impresso)}.")
        # conferências cruzadas no período da DRE
        rec_dre = rel.dados.loc[rel.dados.classificacao.str.startswith("3.1.1"), "saldo"].sum()
        if imp.receita_mensal is not None:
            rec_nf = imp.receita_mensal.reindex(rel.meses).fillna(0).sum()
            dif = rec_nf - rec_dre
            ok = abs(dif) <= max(1.0, 0.01 * abs(rec_dre))
            imp.cruzadas.append({"item": f"Receita {comp(rel.meses[0])}–{comp(rel.meses[-1])}: notas × DRE", "a": rec_nf,
                                 "b": rec_dre, "diferenca": dif, "situacao": "OK" if ok else "Divergente"})
            if not ok:
                al.atencao("Conferência", f"Receita das notas ({brl(rec_nf)}) difere da DRE ({brl(rec_dre)}) em {brl(dif)}.")
        if folha is not None:
            pessoal = -rel.dados.loc[rel.dados.apply(
                lambda c: dp.conta_dre(c["codigo"], c["classificacao"], c["descricao"])[0] == "FOLHA", axis=1), "saldo"].sum()
            fl = folha.dados[folha.dados.competencia.isin(rel.meses)].proventos.sum()
            imp.cruzadas.append({"item": "Pessoal: extrato da folha (proventos) × contas de pessoal da DRE", "a": fl,
                                 "b": pessoal, "diferenca": fl - pessoal,
                                 "situacao": "OK" if abs(fl - pessoal) < 1 else
                                 "Diferença: mês ainda não contabilizado ou encargos nas contas. O sistema usa o extrato."})
    df = pd.concat(todas, ignore_index=True)
    df["destino_txt"] = df["destino"].map(lambda d: DESTINOS.get(d, d))
    imp.dre_contas = df
    imp.parciais["dre"] = acc.df(COLS_DRE_SEMPRE)
    nao = df[df.destino == "NAO_CLASSIFICADO"]
    if not nao.empty:
        al.atencao("DRE", "Contas sem regra (fora do resultado): " +
                   "; ".join(f"{c.classificacao} {c.descricao} {brl(c.saldo)}" for c in nao.itertuples()) + ".")
    rec_total = df.loc[df.destino == "RECEITA", "saldo"].sum()
    for c in df[df.destino == "despesas"].itertuples():
        if rec_total and abs(c.saldo) > 0.05 * rec_total and re.search(r"CART|DIVERS|OUTRA", normalizar(c.descricao).upper()):
            pct = f"{abs(c.saldo) / rec_total * 100:.1f}".replace(".", ",")
            al.atencao("DRE", f"Conta genérica '{c.descricao}' com {brl(-c.saldo)} ({pct}% da receita) entrou como despesa "
                              "dedutível. Vale abrir a natureza: gasto indedutível, pessoal ou insumo com crédito.")
    if base_atual is not None and len(base_atual.meses):
        aluguel = base_atual.dados["cred_aluguel"].fillna(0).sum()
        if aluguel and not df.descricao.map(lambda d: "ALUGUE" in normalizar(d).upper()).any():
            al.atencao("DRE", f"A base tem {brl(aluguel)} de aluguel com crédito, mas a DRE não tem conta de aluguel. "
                              "Confirme o contrato com PJ; sem ele, retire o valor da base de crédito.")
