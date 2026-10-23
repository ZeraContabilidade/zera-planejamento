"""Importação dos relatórios do Domínio: lê, mostra a conferência e só grava quando o usuário confirma."""
import datetime as dt

import pandas as pd
import streamlit as st

from zera_planejamento.app import visual as v
from zera_planejamento.app.estado import base_do, exigir_cliente, mostrar_alertas, tabela_brl
from zera_planejamento.base import COLUNAS
from zera_planejamento.dominio import importar_relatorios
from zera_planejamento.formatos import comp

c = exigir_cliente()
v.cabecalho("Importar relatórios do Domínio", f"Cliente · {c.nome}", "Serviços, saídas, entradas, extrato da folha e DRE, em Excel.")
st.markdown(
    "Envie os relatórios exportados em Excel (o .xls do Domínio, sem converter). O sistema reconhece cada um pelo título: "
    "**Acompanhamento de Serviços**, **Acompanhamento de Saídas**, **Acompanhamento de Entradas**, **Extrato Mensal** "
    "(folha) e **D.R.E.** Para a RBT12 sair certa, exporte desde janeiro do ano anterior; para o Lucro Real, uma DRE por mês.")

arquivos = st.file_uploader("Relatórios", type=["xls", "xlsx"], accept_multiple_files=True)
if arquivos and st.button("Ler relatórios", type="primary", icon=":material/plagiarism:"):
    pasta = c.pasta() / "importacoes" / f"{dt.datetime.now():%Y%m%d-%H%M%S}"
    pasta.mkdir(parents=True, exist_ok=True)
    caminhos = []
    for a in arquivos:
        destino = pasta / a.name
        destino.write_bytes(a.getbuffer())
        caminhos.append(destino)
    try:
        imp = importar_relatorios(caminhos, c, base_do(c))
    except (ValueError, FileNotFoundError) as erro:
        st.error(f"Não foi possível ler: {erro}")
        st.stop()
    st.session_state["importacao"] = (c.id, imp, pasta)

if "importacao" not in st.session_state or st.session_state["importacao"][0] != c.id:
    st.stop()
_, imp, pasta = st.session_state["importacao"]

st.subheader("Relatórios reconhecidos")
st.dataframe(pd.DataFrame([{"Arquivo": r.arquivo, "Relatório": r.tipo, "Empresa": r.empresa, "CNPJ": r.cnpj,
                            "De": r.inicio, "Até": r.fim, "Linhas": len(r.dados)} for r in imp.relatorios]),
             hide_index=True, width="stretch")

mostrar_alertas(imp.alertas.como_df(), "Conferência da importação")

st.subheader("O que será gravado na base mensal")
st.caption("Só os meses do período de cada relatório. Nesses meses, as linhas alimentadas recebem zero quando não há movimento.")
for tipo, parcial in imp.parciais.items():
    if parcial is None:
        continue
    with st.expander(f"{tipo.capitalize()} — {comp(parcial.index[0])} a {comp(parcial.index[-1])}", expanded=tipo == "receita"):
        t = parcial.T
        t.index = [COLUNAS[i][1] for i in t.index]
        t.columns = [comp(p) for p in t.columns]
        st.dataframe(tabela_brl(t), width="stretch")

if imp.cruzadas:
    st.subheader("Conferências cruzadas")
    cz = pd.DataFrame(imp.cruzadas).rename(columns={"item": "Item", "a": "Relatório A", "b": "Relatório B",
                                                    "diferenca": "Diferença", "situacao": "Situação"})
    st.dataframe(tabela_brl(cz), hide_index=True, width="stretch")
if imp.entradas_cfop is not None:
    with st.expander("Entradas por CFOP"):
        e = imp.entradas_cfop[["cfop", "notas", "valor", "destino_txt", "regra"]]
        e.columns = ["CFOP", "Notas", "Valor contábil", "Destino", "Regra"]
        st.dataframe(tabela_brl(e.assign(Notas=e["Notas"].astype(str))), hide_index=True, width="stretch")
if imp.dre_contas is not None:
    with st.expander("DRE por conta"):
        d = imp.dre_contas[["classificacao", "descricao", "periodo", "saldo", "destino_txt", "regra"]]
        d.columns = ["Classificação", "Conta", "Período", "Saldo", "Destino", "Regra"]
        st.dataframe(tabela_brl(d), hide_index=True, width="stretch")
if imp.folha_resumo is not None:
    with st.expander("Folha por competência"):
        f = imp.folha_resumo.copy()
        f["competencia"] = f["competencia"].map(comp)
        f.columns = ["Competência", "Empregados (base INSS)", "Pró-labore", "FGTS", "Proventos", "Pessoas"]
        st.dataframe(tabela_brl(f.assign(Pessoas=f["Pessoas"].astype(str))), hide_index=True, width="stretch")

st.divider()
criticos = imp.alertas.contagem()["CRÍTICO"]
if criticos:
    st.error(f"{criticos} alerta(s) crítico(s). Resolva antes de gravar (ex.: relatório de outra empresa ou lido incompleto).")
if st.button("Gravar na base do cliente", type="primary", icon=":material/save:", disabled=bool(criticos)):
    base = base_do(c)
    n = imp.aplicar(base)
    base.salvar(c.pasta())
    with pd.ExcelWriter(pasta / "conferencia.xlsx") as w:
        imp.alertas.como_df().to_excel(w, sheet_name="Alertas", index=False)
        if imp.entradas_cfop is not None:
            imp.entradas_cfop.to_excel(w, sheet_name="Entradas por CFOP", index=False)
        if imp.dre_contas is not None:
            imp.dre_contas.to_excel(w, sheet_name="DRE por conta", index=False)
    del st.session_state["importacao"]
    st.success(f"{n} valores gravados. Relatórios originais e conferência guardados em {pasta}.", icon=":material/check:")
    a, b = st.columns(2)
    a.page_link("paginas/dashboard.py", label="Ver o dashboard do cliente", icon=":material/dashboard:")
    b.page_link("paginas/base.py", label="Conferir a base mensal", icon=":material/table_view:")
