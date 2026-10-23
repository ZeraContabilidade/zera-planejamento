"""Geração e download dos relatórios (Excel e PDF)."""
import streamlit as st

from zera_planejamento.app import visual as v
from zera_planejamento.app.estado import base_do, exigir_cliente, planejamento_do
from zera_planejamento.configuracoes import Configuracoes
from zera_planejamento.relatorio import gerar_relatorios

c = exigir_cliente()
v.cabecalho("Relatórios", f"Análise · {c.nome}", "Excel auditável e PDF técnico com o timbrado da Zera.")
cfg = Configuracoes.carregar()
if cfg.kit is None:
    st.warning("Kit de identidade visual não configurado: o PDF sai sem o timbrado da Zera. Ajuste em Configurações.",
               icon=":material/palette:")

if st.button("Gerar Excel e PDF", type="primary", icon=":material/description:"):
    try:
        pl = planejamento_do(c, base_do(c), com_equilibrio=True)
    except ValueError as erro:
        st.info(str(erro))
        st.stop()
    with st.spinner("Gerando gráficos, Excel e PDF..."):
        st.session_state["ultimos_relatorios"] = gerar_relatorios(pl, c.pasta() / "relatorios")
    st.success("Relatórios gerados. Revise antes de enviar ao cliente.", icon=":material/check:")

arqs = st.session_state.get("ultimos_relatorios")
if arqs:
    a, b = st.columns(2)
    a.download_button("Baixar Excel", arqs["excel"].read_bytes(), file_name=arqs["excel"].name, icon=":material/table:")
    b.download_button("Baixar PDF", arqs["pdf"].read_bytes(), file_name=arqs["pdf"].name, icon=":material/picture_as_pdf:")
    st.caption(f"Salvos em {arqs['pdf'].parent}")

st.subheader("Gerados anteriormente")
anteriores = sorted((c.pasta() / "relatorios").glob("*/*.pdf"), reverse=True)
if not anteriores:
    st.caption("Nenhum ainda.")
for p in anteriores[:15]:
    col1, col2 = st.columns([4, 1])
    col1.write(f"{p.parent.name} — {p.name}")
    col2.download_button("PDF", p.read_bytes(), file_name=p.name, key=str(p))
