"""Mesa do escritório: a carteira inteira de relance — clientes, roteiro de cada um e a agenda de decisões."""
import datetime as dt

import streamlit as st

from zera_planejamento.app import visual as v
from zera_planejamento.app.estado import base_do, clientes, passos_do
from zera_planejamento.calculo import ROTULO
from zera_planejamento.configuracoes import Configuracoes
from zera_planejamento.formatos import MESES, brl_curto
from zera_planejamento.prazos import prazos

hoje = dt.date.today()
v.cabecalho("Mesa do escritório", "Zera Contabilidade · planejamento tributário",
            f"{hoje.day} de {['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro'][hoje.month - 1]} de {hoje.year} · a carteira inteira de relance")

if st.session_state.pop("_abrir_dashboard", False):
    st.switch_page("paginas/dashboard.py")


def _abrir(cid: str) -> None:
    st.session_state["cliente_id"] = cid
    st.session_state["_abrir_dashboard"] = True
    st.session_state.pop("novo_cliente", None)


def _novo() -> None:
    st.session_state["cliente_id"] = None
    st.session_state["novo_cliente"] = True
    st.session_state["_ir_cadastro"] = True


lista = clientes()
cfg = Configuracoes.carregar()
if not lista:
    v.saudacao(cfg.responsavel.replace("Equipe ", "equipe "), "Nenhum cliente cadastrado ainda.")
    v.faixa("Comece cadastrando o primeiro cliente", "Digite o CNPJ e o sistema busca os dados na Receita Federal. "
            "Depois importe os relatórios do Domínio.", "Primeiro passo")
    st.page_link("paginas/cadastro.py", label="Cadastrar cliente", icon=":material/person_add:")
    st.stop()

# ---------------- situação de cada cliente (só leitura de arquivos: rápido) ----------------
fichas = []
for c in lista:
    base = base_do(c)
    rb = base.receita_bruta()
    meses_receita = rb[rb > 0]
    passos = passos_do(c, base)
    fichas.append({"cliente": c, "passos": passos, "feitos": sum(p["feito"] for p in passos),
                   "receita_12m": float(meses_receita.tail(12).sum()), "ultimo": meses_receita.index.max()
                   if len(meses_receita) else None})
agenda = prazos(lista[0], None, hoje)
proximo = agenda.iloc[0] if not agenda.empty else None
completos = sum(f["feitos"] == len(f["passos"]) for f in fichas)
com_base = sum(f["ultimo"] is not None for f in fichas)

v.saudacao(cfg.responsavel.replace("Equipe ", "equipe "),
           f"{len(lista)} cliente(s) na carteira · {com_base} com base importada · {completos} com o roteiro completo")
cart = [{"l": "Clientes", "v": str(len(lista)), "d": f"{com_base} com base importada"},
        {"l": "Roteiro completo", "v": f"{completos}/{len(lista)}", "d": "cadastro, base, DRE, sócios e parecer"},
        {"l": "Receita da carteira", "v": brl_curto(sum(f["receita_12m"] for f in fichas)), "d": "últimos 12 meses"}]
if proximo is not None:
    cart.append({"l": "Próxima decisão", "v": f"{proximo['data']:%d/%m}", "d": f"em {proximo['dias']} dias",
                 "escuro": True})
v.kpis(cart)

# ---------------- agenda ----------------
a, b = st.columns([1.25, 1])
with a:
    v.rotulo("Agenda de decisões tributárias")
    v.prazos_html([(f"{z.data:%d/%m/%Y}", f"em {z.dias} dias", "PRAZO" if z.acao == "INFORMATIVO" else z.acao,
                    z.evento) for z in agenda.head(4).itertuples()])
with b:
    v.rotulo("Atalhos")
    st.page_link("paginas/carteira.py", label="Painel da carteira — quem deve mudar de regime",
                 icon=":material/groups:")
    st.page_link("paginas/documentos.py", label="Importar outros documentos (Excel, PDF)",
                 icon=":material/note_stack_add:")
    st.page_link("paginas/simulador.py", label="Simulador “E se…”", icon=":material/tune:")
    st.button("Novo cliente", icon=":material/person_add:", on_click=_novo, key="novo_mesa")
    if st.session_state.pop("_ir_cadastro", False):
        st.switch_page("paginas/cadastro.py")

# ---------------- clientes ----------------
v.rotulo("Clientes")
busca = st.text_input("Buscar cliente", placeholder="nome ou CNPJ", label_visibility="collapsed")
filtro = busca.strip().lower()
mostrar = [f for f in fichas if not filtro or filtro in f["cliente"].nome.lower() or filtro in f["cliente"].cnpj]
mostrar.sort(key=lambda f: (f["feitos"] == len(f["passos"]), f["cliente"].nome))
colunas = st.columns(3)
for i, f in enumerate(mostrar):
    c = f["cliente"]
    pendente = next((p["rotulo"] for p in f["passos"] if not p["feito"]), None)
    meta = f"{ROTULO.get(c.regime_atual, c.regime_atual)} · " + (
        f"receita 12m {brl_curto(f['receita_12m'])} · até {MESES[f['ultimo'].month - 1]}/{str(f['ultimo'].year)[2:]}"
        if f["ultimo"] is not None else "sem base importada")
    meta = meta.replace("R$ ", "R$ ")       # "R$" não quebra a linha separado do valor
    tags = [(f"Falta: {pendente}", False)] if pendente else [("Roteiro completo", True)]
    with colunas[i % 3].container(border=True):
        v.cartao_cliente(c.nome, meta, f["feitos"] / len(f["passos"]), tags)
        st.button("Abrir dashboard", key=f"abrir_{c.id}", on_click=_abrir, args=(c.id,), icon=":material/dashboard:",
                  width="stretch")
if not mostrar:
    st.caption("Nenhum cliente encontrado.")
v.rodape("Rascunho técnico — revisar antes de enviar ao cliente")
