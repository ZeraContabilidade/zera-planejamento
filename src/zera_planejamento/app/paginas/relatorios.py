"""Geração e download: parecer ao cliente (Word + PDF) e relatórios internos (Excel e PDF técnico)."""
import streamlit as st

from zera_planejamento.app import visual as v
from zera_planejamento.app.estado import base_do, exigir_cliente, planejamento_do
from zera_planejamento.configuracoes import Configuracoes
from zera_planejamento.projecao import CENARIOS
from zera_planejamento.relatorio import gerar_relatorios
from zera_planejamento.relatorio.parecer import gerar_parecer

c = exigir_cliente()
v.cabecalho("Relatórios", f"Análise · {c.nome}", "Parecer para o cliente e relatórios internos, com o timbrado da Zera.")
cfg = Configuracoes.carregar()

# ---------------- parecer ao cliente ----------------
v.rotulo("Para o cliente · parecer em Word e PDF")
st.markdown("Uma página em linguagem simples: **o que recomendamos, quanto custa, o que muda e até quando decidir**. "
            "Revise o texto no Word antes de enviar; o PDF é a versão para mandar ao cliente.")
a, b = st.columns([1, 2], vertical_alignment="bottom")
cenario = a.selectbox("Cenário do parecer", CENARIOS, help="Normalmente o Neutro.")
if b.button("Gerar parecer ao cliente", type="primary", icon=":material/contract_edit:"):
    try:
        pl = planejamento_do(c, base_do(c))
        with st.spinner("Escrevendo o parecer..."):
            st.session_state[f"parecer_{c.id}"] = gerar_parecer(pl, c.pasta() / "relatorios" / "pareceres", cenario,
                                                                cfg.responsavel)
        st.success("Parecer gerado. Revise antes de enviar.", icon=":material/check:")
    except ValueError as erro:
        st.info(str(erro))
par = st.session_state.get(f"parecer_{c.id}")
if par:
    a, b = st.columns(2)
    a.download_button("Baixar Word (.docx)", par["docx"].read_bytes(), file_name=par["docx"].name,
                      icon=":material/description:", width="stretch")
    b.download_button("Baixar PDF", par["pdf"].read_bytes(), file_name=par["pdf"].name,
                      icon=":material/picture_as_pdf:", width="stretch")

# ---------------- relatórios internos ----------------
v.rotulo("Uso interno · Excel auditável e PDF técnico")
if cfg.kit is None:
    st.warning("Kit de identidade visual não configurado: o PDF técnico sai sem o timbrado. Ajuste em Configurações.",
               icon=":material/palette:")
if st.button("Gerar Excel e PDF técnico", icon=":material/table:"):
    try:
        pl = planejamento_do(c, base_do(c), com_equilibrio=True)
    except ValueError as erro:
        st.info(str(erro))
        st.stop()
    with st.spinner("Gerando gráficos, Excel e PDF..."):
        st.session_state[f"relatorios_{c.id}"] = gerar_relatorios(pl, c.pasta() / "relatorios")
    st.success("Relatórios gerados. Revise antes de usar.", icon=":material/check:")
arqs = st.session_state.get(f"relatorios_{c.id}")
if arqs:
    a, b = st.columns(2)
    a.download_button("Baixar Excel", arqs["excel"].read_bytes(), file_name=arqs["excel"].name, icon=":material/table:",
                      width="stretch")
    b.download_button("Baixar PDF técnico", arqs["pdf"].read_bytes(), file_name=arqs["pdf"].name,
                      icon=":material/picture_as_pdf:", width="stretch")
    st.caption(f"Salvos em {arqs['pdf'].parent}")

# ---------------- histórico ----------------
v.rotulo("Gerados anteriormente")
pasta = c.pasta() / "relatorios"
anteriores = sorted(list(pasta.glob("*/*.pdf")) + list(pasta.glob("pareceres/*.docx")),
                    key=lambda p: p.stat().st_mtime, reverse=True)
if not anteriores:
    st.caption("Nenhum ainda.")
for p in anteriores[:15]:
    col1, col2 = st.columns([4, 1])
    tipo = "Parecer" if p.parent.name == "pareceres" else "Técnico"
    col1.write(f"**{tipo}** · {p.name}")
    col2.download_button(p.suffix.upper().strip("."), p.read_bytes(), file_name=p.name, key=str(p), width="stretch")
