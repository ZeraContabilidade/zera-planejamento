"""Estado compartilhado entre as páginas do app (cliente selecionado, base, cache do planejamento)."""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict

import pandas as pd
import streamlit as st

from zera_planejamento.base import BaseMensal
from zera_planejamento.cliente import Cliente, listar_clientes, pasta_dados
from zera_planejamento.formatos import brl, pct

ICONE_NIVEL = {"CRÍTICO": ":material/error:", "ATENÇÃO": ":material/warning:", "INFO": ":material/info:"}


def clientes() -> list[Cliente]:
    return listar_clientes()


def cliente_atual() -> Cliente | None:
    cid = st.session_state.get("cliente_id")
    for c in clientes():
        if c.id == cid:
            return c
    return None


def exigir_cliente() -> Cliente:
    c = cliente_atual()
    if c is None:
        st.info("Escolha ou cadastre um cliente na barra lateral para continuar.", icon=":material/person_search:")
        st.stop()
    return c


def base_do(cliente: Cliente) -> BaseMensal:
    return BaseMensal.carregar(cliente.pasta())


def assinatura(cliente: Cliente, base: BaseMensal) -> str:
    texto = json.dumps(asdict(cliente), sort_keys=True, default=str) + base.dados.to_csv()
    return hashlib.sha1(texto.encode()).hexdigest()


def planejamento_do(cliente: Cliente, base: BaseMensal):
    """Calcula uma vez por combinação cliente+base (o break-even leva alguns segundos)."""
    from zera_planejamento.planejamento import gerar_planejamento
    chave = assinatura(cliente, base)
    cache = st.session_state.setdefault("_planejamentos", {})
    if chave not in cache:
        with st.spinner("Calculando os regimes, os cenários e os pontos de equilíbrio..."):
            cache.clear()
            cache[chave] = gerar_planejamento(cliente, base)
    return cache[chave]


def mostrar_alertas(df: pd.DataFrame, titulo: str = "Alertas") -> None:
    if df is None or df.empty:
        st.success("Nenhum alerta.", icon=":material/check_circle:")
        return
    cont = df["nivel"].value_counts()
    st.markdown(f"**{titulo}** — " + " · ".join(f"{n}: {cont.get(n, 0)}" for n in ("CRÍTICO", "ATENÇÃO", "INFO")))
    for a in df.itertuples():
        msg = f"**{a.origem}** — {a.mensagem}"
        if a.nivel == "CRÍTICO":
            st.error(msg, icon=ICONE_NIVEL[a.nivel])
        elif a.nivel == "ATENÇÃO":
            st.warning(msg, icon=ICONE_NIVEL[a.nivel])
        else:
            st.info(msg, icon=ICONE_NIVEL[a.nivel])


def tabela_brl(df: pd.DataFrame, colunas_pct: tuple[str, ...] = ()) -> pd.DataFrame:
    """Cópia formatada em texto (R$ e %) para exibir."""
    out = df.copy()
    for c in out.columns:
        if c in colunas_pct:
            out[c] = out[c].map(pct)
        elif pd.api.types.is_numeric_dtype(out[c]) and not pd.api.types.is_bool_dtype(out[c]):
            out[c] = out[c].map(brl)
    return out


__all__ = ["clientes", "cliente_atual", "exigir_cliente", "base_do", "planejamento_do", "mostrar_alertas",
           "tabela_brl", "pasta_dados"]
