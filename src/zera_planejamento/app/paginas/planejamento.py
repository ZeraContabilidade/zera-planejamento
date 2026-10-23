"""Planejamento: regime de menor carga, cenários, equilíbrio, transição e alertas."""
import altair as alt
import pandas as pd
import streamlit as st

from zera_planejamento.app import visual as v
from zera_planejamento.app.estado import base_do, exigir_cliente, md, mostrar_alertas, planejamento_do, tabela_brl
from zera_planejamento.calculo import ROTULO
from zera_planejamento.formatos import brl, comp, pct
from zera_planejamento.relatorio.graficos import COR

c = exigir_cliente()
base = base_do(c)
try:
    pl = planejamento_do(c, base, com_equilibrio=True)
except ValueError as erro:
    st.info(str(erro))
    st.stop()

mh, mp = pl.meses_historico, pl.meses_projetados
v.cabecalho("Planejamento tributário", f"Análise · {c.nome}", f"Histórico {comp(mh[0])} a {comp(mh[-1])} · projeção {comp(mp[0])} a {comp(mp[-1])} · rascunho para revisão")
escala = alt.Scale(domain=[ROTULO[r] for r in COR], range=list(COR.values()))
EIXO_RS = alt.Axis(labelExpr="'R$ ' + format(datum.value / 1000, ',.0f') + ' mil'")
CURTO = {"simples": "Simples", "simples_hibrido": "Simples híbrido", "presumido": "Presumido", "real": "Real"}

m = pl.melhor("Neutro")
if m is not None:
    k = st.columns(4)
    k[0].metric("Menor carga (Neutro)", CURTO[m["regime"]], help=m["rotulo"])
    k[1].metric("Tributos no período", brl(m["tributos"], 0))
    k[2].metric("Carga efetiva", pct(m["carga"]))
    k[3].metric("Economia sobre o 2º", brl(m["economia_vs_2o"], 0))

if pl.prazos is not None and not pl.prazos.empty:
    st.subheader("Próximos prazos de decisão")
    pz = pl.prazos.copy()
    pz["data"] = pd.to_datetime(pz["data"]).dt.strftime("%d/%m/%Y")
    pz = pz[["data", "dias", "acao", "evento", "base_legal"]]
    pz.columns = ["Data", "Dias", "Ação", "Evento", "Base legal"]
    st.dataframe(pz, hide_index=True, width="stretch")

if pl.socios is not None and not pl.socios.vazia:
    ms = pl.socios.resumo[pl.socios.resumo.melhor].iloc[0]
    st.info(md(f"Somando a retirada dos sócios (Lei 15.270/2025), a menor carga total é no **{ms['rotulo']}**: "
               f"{brl(ms['carga_total'], 0)} ({pct(ms['carga_pct'])}). Detalhes em *Sócios e pró-labore*."),
            icon=":material/group:")

st.subheader("Cenários do período projetado")
r = pl.resumo.copy()
r["Regime"] = r["rotulo"]
graf = alt.Chart(r[r.elegivel]).mark_bar(cornerRadiusEnd=3).encode(
    x=alt.X("cenario:N", title=None, sort=["Neutro", "Otimista", "Pessimista"], axis=alt.Axis(labelAngle=0)),
    xOffset="Regime:N", y=alt.Y("tributos:Q", title=None, axis=EIXO_RS),
    color=alt.Color("Regime:N", scale=escala, legend=alt.Legend(orient="top")),
    stroke=alt.condition("datum.melhor", alt.value("#111111"), alt.value(None)), strokeWidth=alt.value(2),
    tooltip=["cenario", "Regime", alt.Tooltip("tributos:Q", format=",.2f"), alt.Tooltip("carga:Q", format=".2%")])
st.altair_chart(graf.properties(height=320), width="stretch")
tab = r[["cenario", "rotulo", "receita", "tributos", "carga", "melhor", "economia_vs_2o"]].copy()
tab["economia_vs_2o"] = tab["economia_vs_2o"].where(tab["melhor"])
tab["melhor"] = tab["melhor"].map({True: "MENOR CARGA", False: ""})
tab.columns = ["Cenário", "Regime", "Receita", "Tributos", "Carga", "Situação", "Economia vs. 2º"]
st.dataframe(tabela_brl(tab, ("Carga",)), hide_index=True, width="stretch")

st.subheader("Pontos de equilíbrio")
for e in pl.equilibrio.itertuples():
    f = (lambda v: pct(v, 1)) if e.unidade == "%" else (lambda v: brl(v, 0))
    st.markdown(md(f"**{e.comparacao}** — equilíbrio {f(e.equilibrio)} · projetado {f(e.projetado)}  \n{e.leitura}"))
if pl.curva is not None and not pl.curva.empty:
    cv = pl.curva.melt("margem", var_name="regime", value_name="tributos").dropna()
    cv["Regime"] = cv["regime"].map(ROTULO)
    linha = alt.Chart(cv).mark_line(strokeWidth=2).encode(
        x=alt.X("margem:Q", title="Margem operacional", axis=alt.Axis(format="%")), y=alt.Y("tributos:Q", title=None, axis=EIXO_RS),
        color=alt.Color("Regime:N", scale=escala, legend=alt.Legend(orient="top")),
        tooltip=[alt.Tooltip("margem:Q", format=".1%"), "Regime", alt.Tooltip("tributos:Q", format=",.0f")])
    regra = alt.Chart(pd.DataFrame({"m": [pl.margem_projetada]})).mark_rule(strokeDash=[4, 4], color="#5F5F5F").encode(x="m:Q")
    st.altair_chart((linha + regra).properties(height=280), width="stretch")

st.subheader("Histórico mês a mês")
mensal = pl.historico.mensal().loc[mh]
h = mensal.reset_index().melt("competencia", var_name="regime", value_name="tributos").dropna()
h["mes"] = h["competencia"].dt.to_timestamp()
h["Regime"] = h["regime"].map(ROTULO)
st.altair_chart(alt.Chart(h).mark_line(point=True).encode(
    x=alt.X("yearmonth(mes):T", title=None), y=alt.Y("tributos:Q", title=None, axis=EIXO_RS),
    color=alt.Color("Regime:N", scale=escala, legend=alt.Legend(orient="top")),
    tooltip=[alt.Tooltip("yearmonth(mes):T", title="Mês"), "Regime", alt.Tooltip("tributos:Q", format=",.2f")]
).properties(height=300), width="stretch")

if pl.transicao is not None and not pl.transicao.empty:
    st.subheader("Transição da Reforma (2026–2033)")
    st.caption("Os últimos 12 meses sob a regra de cada ano. CBS/IBS de referência editáveis no cadastro.")
    t = pl.transicao.drop(columns="receita").reset_index().melt("ano", var_name="regime", value_name="tributos").dropna()
    t["Regime"] = t["regime"].map(ROTULO)
    st.altair_chart(alt.Chart(t).mark_line(point=True).encode(
        x=alt.X("ano:O", title=None), y=alt.Y("tributos:Q", title=None, axis=EIXO_RS),
        color=alt.Color("Regime:N", scale=escala, legend=alt.Legend(orient="top")),
        tooltip=["ano", "Regime", alt.Tooltip("tributos:Q", format=",.0f")]).properties(height=280),
        width="stretch")
    tt = pl.transicao.copy()
    tt.columns = [ROTULO.get(col, "Receita") for col in tt.columns]
    st.dataframe(tabela_brl(tt), width="stretch")

mostrar_alertas(pl.alertas.como_df())
with st.expander("Regras ainda a conferir"):
    for p in pl.pendencias:
        st.markdown(md(f"- {p}"))
