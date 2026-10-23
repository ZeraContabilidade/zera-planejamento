"""Configurações do escritório e regras pendentes de conferência."""
from pathlib import Path

import streamlit as st

from zera_planejamento.app.estado import md
from zera_planejamento.cliente import pasta_dados
from zera_planejamento.configuracoes import Configuracoes
from zera_planejamento.regras import pendencias_conferir

st.title("Configurações")
cfg = Configuracoes.carregar()
with st.form("cfg"):
    kit = st.text_input("Pasta do kit de identidade visual (ZERA - IDENTIDADE VISUAL)", cfg.kit_identidade,
                        help="Precisa ter header_a4.png, logo_zera_fundo_preto.png e a pasta fonts/ (Cormorant Garamond e Inter).")
    resp = st.text_input("Assinatura dos relatórios", cfg.responsavel)
    esc = st.text_input("Rodapé do PDF", cfg.escritorio)
    if st.form_submit_button("Salvar", type="primary"):
        Configuracoes(kit_identidade=kit, responsavel=resp, escritorio=esc).salvar()
        st.success("Salvo.")
p = Path(kit) if kit else None
if p and p.exists():
    faltam = [n for n in ("header_a4.png", "logo_zera_fundo_preto.png", "fonts") if not (p / n).exists()]
    st.write("Kit encontrado." if not faltam else f"Kit encontrado, mas faltam: {', '.join(faltam)}")
elif kit:
    st.warning("Pasta do kit não encontrada neste computador.")

st.caption(f"Dados dos clientes em `{pasta_dados()}` (variável de ambiente ZERA_DADOS).")
st.subheader("Regras a conferir")
for t in pendencias_conferir():
    st.markdown(md(f"- {t}"))
