"""Painel da carteira: quem deveria mudar de regime antes de janeiro."""
import io

import pandas as pd
import streamlit as st

from zera_planejamento.app import visual as v
from zera_planejamento.app.estado import clientes, tabela_brl
from zera_planejamento.carteira import analisar_carteira
from zera_planejamento.formatos import brl

v.cabecalho("Painel da carteira", "Escritório · todos os clientes", "Quem deveria mudar de regime (cenário Neutro). A opção é irretratável no ano: use em novembro e dezembro.")
lista = clientes()
st.write(f"{len(lista)} cliente(s) cadastrado(s).")

if st.button("Analisar a carteira", type="primary", icon=":material/groups:", disabled=not lista):
    barra = st.progress(0.0)
    df = analisar_carteira(lista, lambda i, n, nome: barra.progress(i / n, text=f"{i}/{n} — {nome}"))
    barra.empty()
    st.session_state["_carteira"] = df

df = st.session_state.get("_carteira")
if df is not None and not df.empty:
    mudar = df[df.situacao == "MUDAR"]
    k = st.columns(3)
    k[0].metric("Mudar de regime", len(mudar))
    k[1].metric("Avaliar", int((df.situacao == "AVALIAR").sum()))
    k[2].metric("Economia anual estimada", brl(mudar["economia_ano"].sum() if "economia_ano" in mudar else 0, 0))
    cols = [c for c in ["situacao", "cliente", "cnpj", "regime_atual", "menor_carga", "custo_atual_ano",
                        "custo_menor_ano", "economia_ano", "carga_menor", "alertas_criticos", "decidir_ate", "leitura"]
            if c in df]
    tab = df[cols].copy()
    if "alertas_criticos" in tab:
        tab["alertas_criticos"] = tab["alertas_criticos"].astype("Int64").astype(str).replace("<NA>", "")
    tab = tabela_brl(tab, ("carga_menor",))
    tab = tab.rename(columns={"situacao": "Situação", "cliente": "Cliente", "cnpj": "CNPJ", "regime_atual": "Regime atual",
                              "menor_carga": "Menor carga", "custo_atual_ano": "Custo atual (ano)",
                              "custo_menor_ano": "Custo menor (ano)", "economia_ano": "Economia (ano)",
                              "carga_menor": "Carga", "alertas_criticos": "Críticos", "decidir_ate": "Decidir até",
                              "leitura": "Leitura"})
    st.dataframe(tab, hide_index=True, width="stretch")
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        df.to_excel(xw, sheet_name="Carteira", index=False)
    st.download_button("Baixar Excel da carteira", buf.getvalue(), file_name="painel_carteira.xlsx",
                       icon=":material/table:")
    st.caption("Estimativa anualizada a partir dos meses projetados. Rascunho técnico: revisar cada cliente antes de "
               "recomendar a mudança.")
