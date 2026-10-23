"""
App da equipe (Streamlit). Rodar com:  zera-planejamento app   (ou iniciar.bat no Windows)
"""
from __future__ import annotations

import streamlit as st

from zera_planejamento import __version__
from zera_planejamento.app.estado import base_do, cliente_atual, clientes, pasta_dados, passos_do
from zera_planejamento.app.visual import aplicar_identidade

st.set_page_config(page_title="Zera Planejamento Tributário", page_icon=":material/account_balance:", layout="wide")
aplicar_identidade()

paginas = {
    "Visão geral": [
        st.Page("paginas/dashboard.py", title="Dashboard", icon=":material/dashboard:", default=True),
    ],
    "Cliente": [
        st.Page("paginas/cadastro.py", title="Cadastro", icon=":material/badge:"),
        st.Page("paginas/importar.py", title="Importar Domínio", icon=":material/upload_file:"),
        st.Page("paginas/base.py", title="Base mensal", icon=":material/table_view:"),
    ],
    "Análise": [
        st.Page("paginas/planejamento.py", title="Planejamento", icon=":material/insights:"),
        st.Page("paginas/socios.py", title="Sócios e pró-labore", icon=":material/group:"),
        st.Page("paginas/relatorios.py", title="Relatórios", icon=":material/picture_as_pdf:"),
    ],
    "Escritório": [
        st.Page("paginas/carteira.py", title="Painel da carteira", icon=":material/groups:"),
    ],
    "Ajustes": [
        st.Page("paginas/depara.py", title="De-Para", icon=":material/rule:"),
        st.Page("paginas/configuracoes.py", title="Configurações", icon=":material/settings:"),
    ],
}

with st.sidebar:
    lista = clientes()
    opcoes = {c.id: f"{c.nome} — {c.cnpj}" if c.cnpj else c.nome for c in lista}
    atual = cliente_atual()
    if opcoes:
        ids = list(opcoes)
        escolhido = st.selectbox("Cliente", ids, format_func=opcoes.get,
                                 index=ids.index(atual.id) if atual else 0,
                                 on_change=lambda: st.session_state.pop("novo_cliente", None))
        st.session_state["cliente_id"] = escolhido
    else:
        st.caption("Nenhum cliente cadastrado ainda.")
    pagina_por_nome = {pg.url_path: pg for grupo in paginas.values() for pg in grupo}
    atual = cliente_atual()
    if atual is not None and not st.session_state.get("novo_cliente"):
        passos = passos_do(atual, base_do(atual))
        feitos = sum(p["feito"] for p in passos)
        with st.expander(f"Roteiro do cliente · {feitos}/{len(passos)}", expanded=feitos < len(passos),
                         icon=":material/checklist:"):
            for p in passos:
                st.page_link(pagina_por_nome[p["pagina"]], label=p["rotulo"],
                             icon=":material/check_circle:" if p["feito"] else ":material/radio_button_unchecked:",
                             help=p.get("dica"))
        proximo = next((p for p in passos if not p["feito"]), None)
        if proximo:
            st.page_link(pagina_por_nome[proximo["pagina"]], label=f"Próximo: {proximo['rotulo']}",
                         icon=":material/arrow_forward:")
    if st.button("Novo cliente", icon=":material/person_add:", width="stretch"):
        st.session_state["cliente_id"] = None
        st.session_state["novo_cliente"] = True
        st.switch_page(paginas["Cliente"][0])
    st.divider()
    st.caption(f"Dados em `{pasta_dados()}`  \nVersão {__version__} · rascunho técnico para revisão")

st.navigation(paginas).run()
