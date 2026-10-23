"""Sócios: cadastro, carga sócio + empresa (Lei 15.270/2025) e pró-labore ótimo / Fator R."""
import altair as alt
import pandas as pd
import streamlit as st

from zera_planejamento.app import visual as v
from zera_planejamento.app.estado import base_do, exigir_cliente, md, planejamento_do, tabela_brl
from zera_planejamento.calculo import ROTULO
from zera_planejamento.cliente import Socio
from zera_planejamento.formatos import brl, pct
from zera_planejamento.relatorio.graficos import COR
from zera_planejamento.socios import otimizar_pro_labore

c = exigir_cliente()
base = base_do(c)
v.cabecalho("Sócios e pró-labore", f"Análise · {c.nome}", "Retirada dos sócios somada aos tributos da empresa (Lei 15.270/2025) e o pró-labore de menor custo total.")

# ---------------- cadastro ----------------
st.subheader("Sócios")
df = pd.DataFrame([s.__dict__ for s in c.socios],
                  columns=["nome", "participacao", "pro_labore", "dependentes", "outros_rendimentos"])
df["participacao"] = df["participacao"] * 100
with st.form("socios"):
    editado = st.data_editor(
        df, num_rows="dynamic", width="stretch", hide_index=True,
        column_config={
            "nome": st.column_config.TextColumn("Nome", required=True),
            "participacao": st.column_config.NumberColumn("Participação (%)", min_value=0.0, max_value=100.0,
                                                          format="%.2f", required=True),
            "pro_labore": st.column_config.NumberColumn("Pró-labore mensal (R$)", min_value=0.0, format="%.2f",
                                                        help="Vazio = pró-labore da base × participação"),
            "dependentes": st.column_config.NumberColumn("Dependentes IR", min_value=0, step=1),
            "outros_rendimentos": st.column_config.NumberColumn("Outras rendas no ano (R$)", min_value=0.0,
                                                                format="%.2f",
                                                                help="Entram na base do imposto mínimo (IRPFM)"),
        })
    a, b = st.columns(2)
    dist = a.number_input("Lucro distribuído (%)", 0.0, 100.0, c.distribuicao_lucro * 100, 5.0) / 100
    forma = b.selectbox("Forma de distribuição", ["mensal", "anual"], ["mensal", "anual"].index(c.distribuicao_forma),
                        format_func={"mensal": "Mensal (lucro do mês)", "anual": "Um pagamento no período"}.get)
    if st.form_submit_button("Salvar sócios", type="primary", icon=":material/save:"):
        socios = []
        for r in editado.to_dict("records"):
            if not r.get("nome") or pd.isna(r.get("nome")):
                continue
            socios.append(Socio(nome=str(r["nome"]).strip(), participacao=float(r.get("participacao") or 0) / 100,
                                pro_labore=None if pd.isna(r.get("pro_labore")) else float(r["pro_labore"]),
                                dependentes=0 if pd.isna(r.get("dependentes")) else int(r["dependentes"]),
                                outros_rendimentos=0.0 if pd.isna(r.get("outros_rendimentos"))
                                else float(r["outros_rendimentos"])))
        soma = sum(s.participacao for s in socios)
        if socios and abs(soma - 1) > 0.001:
            st.warning(f"As participações somam {pct(soma)}; o cálculo usa a proporção entre elas.")
        c.socios, c.distribuicao_lucro, c.distribuicao_forma = socios, dist, forma
        c.salvar()
        st.success("Sócios salvos.", icon=":material/check:")
        st.rerun()

try:
    pl = planejamento_do(c, base)
except ValueError as erro:
    st.info(str(erro))
    st.stop()
escala = alt.Scale(domain=[ROTULO[r] for r in COR], range=list(COR.values()))

# ---------------- sócio + empresa ----------------
st.subheader("Carga sócio + empresa — período projetado (Neutro)")
v = pl.socios
if v is None or v.vazia:
    for o in (v.observacoes if v else []):
        st.info(md(o))
else:
    r = v.resumo
    m = r[r.melhor].iloc[0]
    k = st.columns(3)
    k[0].metric("Menor carga total", m["rotulo"])
    k[1].metric("Empresa + sócios", brl(m["carga_total"], 0))
    k[2].metric("Carga sobre a receita", pct(m["carga_pct"]))
    tab = r[["rotulo", "tributos_pj", "lucro_contabil", "dividendos", "irrf_dividendos", "irpfm", "inss_socios",
             "irrf_pro_labore", "carga_total", "carga_pct"]].copy()
    tab.columns = ["Regime", "Tributos da empresa", "Lucro contábil", "Lucros distribuídos", "IRRF 10% (antecipação)",
                   "IRPFM", "INSS dos sócios", "IRRF do pró-labore", "Empresa + sócios", "Carga total"]
    st.dataframe(tabela_brl(tab, ("Carga total",)), hide_index=True, width="stretch")
    with st.expander("Detalhe por sócio"):
        det = v.detalhe[["rotulo", "socio", "pro_labore_mes", "dividendos", "dividendos_mes", "irrf_dividendos",
                         "renda_anual", "aliquota_irpfm", "redutor", "irpfm", "ajuste_anual"]].copy()
        det.columns = ["Regime", "Sócio", "Pró-labore/mês", "Lucros no período", "Lucros/mês", "IRRF 10%",
                       "Renda anual", "Alíquota IRPFM", "Redutor", "IRPFM", "Ajuste anual (− restitui)"]
        st.dataframe(tabela_brl(det, ("Alíquota IRPFM",)), hide_index=True, width="stretch")
    for o in v.observacoes:
        st.info(md(o), icon=":material/info:")

# ---------------- otimizador ----------------
st.subheader("Pró-labore de menor custo")
st.caption("Cada valor é testado como se fosse pago nos últimos 12 meses (Fator R estabilizado). Custo = tributos da "
           "empresa + INSS 11% + IRRF dos sócios. Não inclui o efeito sobre os lucros distribuídos.")
if st.button("Calcular pró-labore ótimo", icon=":material/tune:"):
    with st.spinner("Testando valores de pró-labore em cada regime..."):
        st.session_state[f"_otim_{c.id}"] = otimizar_pro_labore(base, c)
o = st.session_state.get(f"_otim_{c.id}")
if o is not None:
    if not o.melhor.empty:
        mm = o.melhor.copy()
        mm.columns = ["Regime", "Pró-labore mensal ótimo", "Custo anual", "Custo com o pró-labore atual", "Economia"]
        st.dataframe(tabela_brl(mm), hide_index=True, width="stretch")
    if o.para_fator_r is not None:
        txt = f"Pró-labore para o Fator R chegar a 28%: **{brl(o.para_fator_r)} por mês** (hoje {brl(o.atual)})."
        if o.meses_ate_anexo_iii:
            txt += f" Começando no próximo mês, o Anexo III passa a valer em cerca de **{o.meses_ate_anexo_iii} meses**."
        st.markdown(md(txt))
    g = o.grade.melt("pro_labore", value_vars=[r for r in ("simples", "presumido", "real") if r in o.grade],
                     var_name="regime", value_name="custo").dropna()
    g["Regime"] = g["regime"].map(ROTULO)
    linha = alt.Chart(g).mark_line(point=True).encode(
        x=alt.X("pro_labore:Q", title="Pró-labore mensal (total dos sócios)"),
        y=alt.Y("custo:Q", title=None, axis=alt.Axis(labelExpr="'R$ ' + format(datum.value / 1000, ',.0f') + ' mil'")),
        color=alt.Color("Regime:N", scale=escala, legend=alt.Legend(orient="top")),
        tooltip=[alt.Tooltip("pro_labore:Q", format=",.2f"), "Regime", alt.Tooltip("custo:Q", format=",.2f")])
    regra = alt.Chart(pd.DataFrame({"x": [o.atual]})).mark_rule(strokeDash=[4, 4], color="#5F5F5F").encode(x="x:Q")
    st.altair_chart((linha + regra).properties(height=320), width="stretch")
