"""Base mensal: ver, ajustar à mão e incluir o histórico que não veio do Domínio."""
import io

import pandas as pd
import streamlit as st

from zera_planejamento.app import visual as v
from zera_planejamento.app.estado import base_do, exigir_cliente
from zera_planejamento.base import COLUNAS, BaseMensal

c = exigir_cliente()
v.cabecalho("Base mensal", f"Cliente · {c.nome}", "Uma coluna por mês. Vazio = não informado. Valores digitados aqui ficam com origem 'manual'.")
base = base_do(c)

with st.expander("Incluir meses", icon=":material/add:"):
    a, b, d = st.columns(3)
    ini = a.text_input("De (AAAA-MM)", "2025-01")
    fim = b.text_input("Até (AAAA-MM)", "2025-12")
    if d.button("Criar meses vazios"):
        try:
            novo = pd.DataFrame(index=pd.period_range(ini, fim, freq="M"), columns=["rec_anexo_i"], dtype=float)
            base._expandir(novo.index.min(), novo.index.max())
            base.salvar(c.pasta())
            st.rerun()
        except ValueError:
            st.error("Use o formato AAAA-MM.")

if len(base.meses) == 0:
    st.info("A base está vazia. Importe os relatórios do Domínio ou inclua meses acima.")
    st.stop()

grupos = {"receita": "Receita", "tributos": "ICMS/ISS (fora do Simples)", "credito": "Base de crédito",
          "folha": "Folha", "resultado": "Resultado (DRE)"}
abas = st.tabs(list(grupos.values()))
alterados = []
for aba, (g, _) in zip(abas, grupos.items()):
    with aba:
        cols = [col for col, (gg, _) in COLUNAS.items() if gg == g]
        t = base.dados[cols].T
        t.index = [COLUNAS[col][1] for col in cols]
        t.columns = [str(p) for p in t.columns]
        editado = st.data_editor(t, key=f"ed_{g}", width="stretch",
                                 column_config={col: st.column_config.NumberColumn(format="%.2f") for col in t.columns})
        diff = editado.compare(t) if editado.shape == t.shape else None
        if diff is not None and not diff.empty:
            novo = editado.T
            novo.columns = cols
            novo.index = pd.PeriodIndex(novo.index, freq="M")
            alterados.append(novo)

if alterados and st.button("Salvar alterações", type="primary", icon=":material/save:"):
    for parcial in alterados:
        antes = base.dados[parcial.columns]
        mudou = parcial.where(~((parcial == antes) | (parcial.isna() & antes.isna())))
        base.mesclar(mudou, "manual")
    base.salvar(c.pasta())
    st.success("Base salva.")
    st.rerun()

st.divider()
st.subheader("Planilha de digitação")
a, b = st.columns(2)
buf = io.BytesIO()
tmp = c.pasta() / "base_para_digitar.xlsx"
base.para_planilha(tmp)
a.download_button("Baixar a base em Excel", tmp.read_bytes(), file_name=f"base_{c.id}.xlsx", icon=":material/download:")
up = b.file_uploader("Enviar planilha preenchida", type=["xlsx"], key="up_base")
if up is not None and b.button("Gravar planilha na base"):
    tmp_up = c.pasta() / "base_enviada.xlsx"
    tmp_up.write_bytes(up.getbuffer())
    base.mesclar(BaseMensal.de_planilha(tmp_up), "planilha manual")
    base.salvar(c.pasta())
    st.success("Planilha gravada.")
    st.rerun()

with st.expander("Origem de cada valor"):
    o = base.origem.T
    o.index = [COLUNAS[i][1] for i in o.index]
    o.columns = [str(p) for p in o.columns]
    st.dataframe(o, width="stretch")
