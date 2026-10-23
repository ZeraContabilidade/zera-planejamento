"""
App da equipe (Streamlit). Rodar com:  zera-planejamento app   (ou iniciar.bat no Windows)
"""
from __future__ import annotations

import streamlit as st

from zera_planejamento import __version__
from zera_planejamento.app.estado import cliente_atual, clientes, pasta_dados

st.set_page_config(page_title="Zera Planejamento Tributário", page_icon=":material/account_balance:", layout="wide")

paginas = {
    "Cliente": [
        st.Page("paginas/cadastro.py", title="Cadastro", icon=":material/badge:", default=True),
        st.Page("paginas/importar.py", title="Importar Domínio", icon=":material/upload_file:"),
        st.Page("paginas/base.py", title="Base mensal", icon=":material/table_view:"),
    ],
    "Análise": [
        st.Page("paginas/planejamento.py", title="Planejamento", icon=":material/insights:"),
        st.Page("paginas/relatorios.py", title="Relatórios", icon=":material/picture_as_pdf:"),
    ],
    "Ajustes": [
        st.Page("paginas/depara.py", title="De-Para", icon=":material/rule:"),
        st.Page("paginas/configuracoes.py", title="Configurações", icon=":material/settings:"),
    ],
}

with st.sidebar:
    st.markdown("### Zera Contabilidade\nPlanejamento tributário")
    lista = clientes()
    opcoes = {c.id: f"{c.nome} — {c.cnpj}" if c.cnpj else c.nome for c in lista}
    atual = cliente_atual()
    if opcoes:
        ids = list(opcoes)
        escolhido = st.selectbox("Cliente", ids, format_func=opcoes.get,
                                 index=ids.index(atual.id) if atual else 0)
        st.session_state["cliente_id"] = escolhido
    else:
        st.caption("Nenhum cliente cadastrado ainda.")
    if st.button("Novo cliente", icon=":material/person_add:", width="stretch"):
        st.session_state["cliente_id"] = None
        st.session_state["novo_cliente"] = True
        st.switch_page(paginas["Cliente"][0])
    st.divider()
    st.caption(f"Dados em `{pasta_dados()}`  \nVersão {__version__} · rascunho técnico para revisão")

st.navigation(paginas).run()
