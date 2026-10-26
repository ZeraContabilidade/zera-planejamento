"""Comparação entre anos: realizado, estimativa do ano corrente e projeção do próximo ano."""
import io

import altair as alt
import pandas as pd
import streamlit as st

from zera_planejamento.app import visual as v
from zera_planejamento.app.estado import base_do, exigir_cliente, md, tabela_brl
from zera_planejamento.calculo import ROTULO
from zera_planejamento.comparativo import METODOS, comparar_anos
from zera_planejamento.formatos import MESES, brl, brl_curto, pct
from zera_planejamento.relatorio.graficos import COR

CURTO = {"simples": "Simples", "simples_hibrido": "Simples híbrido", "presumido": "Presumido", "real": "Real"}
SITUACAO = {"realizado": "Realizado", "parcial": "Realizado (parcial)", "realizado + estimado": "Realizado + estimado",
            "estimado": "Estimado", "projetado": "Projetado"}

c = exigir_cliente()
base = base_do(c)
v.cabecalho("Comparação entre anos", f"Análise · {c.nome}",
            "Realizado de cada ano, estimativa de fechamento do ano corrente e projeção do próximo ano.")

f1, f2, f3 = st.columns([1.6, 1, 1])
CURTO_METODO = {"tendencia": "Tendência", "media": "Média", "crescimento": "Crescimento %"}
metodo = f1.segmented_control("Base da projeção", list(METODOS), default="tendencia", format_func=CURTO_METODO.get,
                              key="anos_metodo", help=" · ".join(METODOS.values())) or "tendencia"
crescimento = None
if metodo == "crescimento":
    crescimento = f2.number_input("Crescimento da receita (%)", -50.0, 200.0, value=None, step=1.0,
                                  placeholder="usar o observado",
                                  help="Vazio = crescimento observado no mesmo período do ano anterior.")
    crescimento = None if crescimento is None else crescimento / 100
variacao = f3.number_input("Variação dos cenários (±%)", 0.0, 50.0, 15.0, 1.0) / 100
try:
    with st.spinner("Calculando os anos..."):
        cp = comparar_anos(base, c, metodo, crescimento, variacao)
except ValueError as erro:
    st.info(str(erro), icon=":material/upload_file:")
    st.page_link("paginas/importar.py", label="Importar relatórios do Domínio", icon=":material/upload_file:")
    st.stop()

anos, a0, a1 = cp.anos, cp.ano_atual, cp.proximo_ano
regimes = [r for r in ("simples", "simples_hibrido", "presumido", "real") if r in anos and anos[r].notna().any()]
if metodo == "crescimento":
    usado = crescimento if crescimento is not None else (cp.crescimento_observado or 0.0)
    st.caption(f"Projeção: média dos últimos 12 meses × (1 {'+' if usado >= 0 else '−'} {pct(abs(usado), 1)}). "
               "Custos e compras acompanham a receita; folha e despesas fixas, não.")

# ---------------- destaque do próximo ano ----------------
prox = anos.loc[a1] if a1 in anos.index else None
if prox is not None and isinstance(prox.get("menor"), str):
    atual = {"simples": "simples", "presumido": "presumido", "real": "real"}.get(c.regime_atual)
    rec_atual = anos.at[a0, "receita"] if a0 in anos.index else None
    cresc = prox["receita"] / rec_atual - 1 if rec_atual else None
    texto = f"Receita projetada de {brl(prox['receita'], 0)}"
    if cresc is not None:
        texto += f" ({'+' if cresc >= 0 else ''}{pct(cresc, 1)} sobre {a0} estimado)"
    if atual and prox["menor"] != atual and pd.notna(prox.get("economia_vs_atual")):
        v.faixa(f"{a1}: menor carga no {ROTULO[prox['menor']]}",
                texto + f". Economia estimada de {brl(prox['economia_vs_atual'], 0)} no ano em relação ao "
                f"{ROTULO.get(atual, '')} — a opção é feita em janeiro.", "Próximo ano")
    else:
        v.faixa(f"{a1}: manter o {ROTULO[prox['menor']]}", texto + ". O regime atual continua o de menor carga.",
                "Próximo ano")

# ---------------- cartões ----------------
cart = []
anteriores = [a for a in anos.index if a < a0]
if anteriores:
    ult = anteriores[-1]
    cart.append({"l": f"Receita {ult}", "v": brl_curto(anos.at[ult, "receita"]),
                 "d": SITUACAO[anos.at[ult, "situacao"]]})
if a0 in anos.index:
    var = anos.at[a0, "var_receita"]
    cart.append({"l": f"Receita {a0}", "v": brl_curto(anos.at[a0, "receita"]),
                 "d": v.variacao(var, f"{pct(var, 1)} sobre {a0 - 1}") if pd.notna(var)
                 else f"{int(anos.at[a0, 'meses_reais'])} meses reais + {int(anos.at[a0, 'meses_estimados'])} estimados"})
if cp.crescimento_observado is not None:
    cart.append({"l": f"Crescimento {cp.periodo_txt}", "v": pct(cp.crescimento_observado, 1),
                 "d": f"{cp.periodo_txt}/{a0} × {cp.periodo_txt}/{a0 - 1}"})
if prox is not None:
    cart.append({"l": f"Receita {a1}", "v": brl_curto(prox["receita"]), "d": "projetada · cenário central"})
    if isinstance(prox.get("menor"), str):
        cart.append({"l": f"Menor carga {a1}", "v": CURTO[prox["menor"]],
                     "d": f"{brl_curto(prox[prox['menor']])} · {pct(prox['carga_' + prox['menor']], 1)}", "escuro": True})
v.kpis(cart)

# ---------------- mesmo período ----------------
if not cp.mesmo_periodo.empty:
    v.rotulo(f"Mesmo período · {cp.periodo_txt}/{a0 - 1} × {cp.periodo_txt}/{a0}")
    mp = cp.mesmo_periodo[["item", "anterior", "atual", "variacao"]].copy()
    mp["diferenca"] = mp["atual"] - mp["anterior"]
    mp = mp[["item", "anterior", "atual", "diferenca", "variacao"]]
    mp.columns = ["Item", f"{cp.periodo_txt}/{a0 - 1}", f"{cp.periodo_txt}/{a0}", "Diferença", "Variação"]
    st.dataframe(tabela_brl(mp, ("Variação",)), hide_index=True, width="stretch")
    st.caption("Comparação justa enquanto o ano não fecha: os mesmos meses nos dois anos, com as regras de cada ano.")

# ---------------- gráficos ----------------
escala = alt.Scale(domain=[ROTULO[r] for r in COR], range=list(COR.values()))
EIXO_RS = alt.Axis(labelExpr="'R$ ' + format(datum.value / 1000, ',.0f') + ' mil'", title=None)
a, b = st.columns([1.15, 1])
t = anos[regimes].reset_index().melt("ano", var_name="regime", value_name="tributos").dropna()
t["Regime"], t["situacao"] = t["regime"].map(ROTULO), t["ano"].map(anos["situacao"]).map(SITUACAO)
t["valor"] = t["tributos"].map(lambda x: brl(x, 0))
t["ano_txt"] = t["ano"].astype(str)
sel = alt.selection_point(fields=["Regime"], bind="legend")
barras = alt.Chart(t).mark_bar(cornerRadiusEnd=3).encode(
    x=alt.X("ano_txt:N", title=None, axis=alt.Axis(labelAngle=0, labelFontSize=12)), xOffset="Regime:N",
    y=alt.Y("tributos:Q", axis=EIXO_RS), color=alt.Color("Regime:N", scale=escala, title=None),
    opacity=alt.condition(sel, alt.value(1), alt.value(0.15)),
    tooltip=[alt.Tooltip("ano_txt:N", title="Ano"), "Regime", alt.Tooltip("valor:N", title="Tributos"),
             alt.Tooltip("situacao:N", title="Situação")]).add_params(sel)
with a:
    v.rotulo("Tributos por ano e regime")
    st.altair_chart(v.grafico(barras, altura=320), width="stretch")
    st.caption("Anos em andamento somam meses reais e estimados; o próximo ano é projetado.")

m = cp.mensal.copy()
m["Mês"] = m["mes"].map(lambda x: MESES[x - 1])
m["Ano"] = m["ano"].astype(str)
m["valor"] = m["receita"].map(lambda x: brl(x, 0))
m["Tipo"] = m["tipo"].map({"real": "Real", "estimado": "Estimado", "projetado": "Projetado"})
cores_anos = ["#BDB3A0", "#8C8C8C", v.PRETO, v.DOURADO, "#2F6EA8"][-len(m["Ano"].unique()):]
linhas = alt.Chart(m).mark_line(point=alt.OverlayMarkDef(size=45, filled=True), strokeWidth=2.2).encode(
    x=alt.X("Mês:N", sort=MESES, title=None, axis=alt.Axis(labelAngle=0)), y=alt.Y("receita:Q", axis=EIXO_RS),
    color=alt.Color("Ano:N", scale=alt.Scale(range=cores_anos), title=None),
    strokeDash=alt.StrokeDash("Tipo:N", scale=alt.Scale(domain=["Real", "Estimado", "Projetado"],
                                                       range=[[1, 0], [5, 3], [2, 3]]), title=None),
    detail="Tipo:N",
    tooltip=["Ano", "Mês", alt.Tooltip("valor:N", title="Receita"), "Tipo"])
with b:
    v.rotulo("Receita mês a mês · um traço por ano")
    st.altair_chart(v.grafico(linhas, altura=320), width="stretch")
    st.caption("Linha cheia = real; tracejada = estimado ou projetado. Mostra sazonalidade e ritmo de cada ano.")

# ---------------- tabela dos anos ----------------
v.rotulo("Resumo por ano")
tab = anos.copy()
tab["Situação"] = tab["situacao"].map(SITUACAO)
tab["Meses"] = tab["meses_reais"].astype(int).astype(str) + " reais" + \
    tab["meses_estimados"].map(lambda n: f" + {int(n)} est." if n else "")
tab["Menor carga"] = tab["menor"].map(lambda r: CURTO.get(r, "") if isinstance(r, str) else "")
colunas = {"Situação": "Situação", "Meses": "Meses", "receita": "Receita", "var_receita": "Variação da receita"}
colunas.update({r: f"Tributos — {CURTO[r]}" for r in regimes})
colunas["Menor carga"] = "Menor carga"
tab = tab[list(colunas)].rename(columns=colunas)
tab.index = tab.index.astype(str)
st.dataframe(tabela_brl(tab.reset_index().rename(columns={"ano": "Ano"}), ("Variação da receita",)),
             hide_index=True, width="stretch")

# ---------------- cenários do próximo ano ----------------
v.rotulo(f"Cenários para {a1} · receita {'±'}{pct(variacao, 0)}")
cz = cp.cenarios.pivot(index="regime", columns="cenario", values="tributos")
cz = cz.reindex(columns=["Pessimista", "Central", "Otimista"]).loc[[r for r in regimes if r in cz.index]]
rec_cen = cp.cenarios.groupby("cenario")["receita"].first().reindex(cz.columns)
cz.index = [ROTULO[r] for r in cz.index]
cz.loc["Receita"] = rec_cen
melhores = cp.cenarios[cp.cenarios["melhor"]].set_index("cenario")["regime"].map(CURTO)
st.dataframe(tabela_brl(cz.reset_index().rename(columns={"index": "Regime"})), hide_index=True, width="stretch")
st.caption(md("Menor carga por cenário — " + " · ".join(f"{k}: {val}" for k, val in melhores.items()) +
              f". Regras de {a1}: CBS/IBS com alíquotas de referência estimadas e RBT12 sem o mês anterior."))

if cp.alertas.itens:
    with st.expander(f"Avisos da projeção ({len(cp.alertas.itens)})"):
        for al in cp.alertas.itens:
            st.markdown(md(f"- **{al.nivel} · {al.origem}** — {al.mensagem}"))

buf = io.BytesIO()
with pd.ExcelWriter(buf, engine="openpyxl") as xw:
    anos.to_excel(xw, sheet_name="Por ano")
    if not cp.mesmo_periodo.empty:
        cp.mesmo_periodo.to_excel(xw, sheet_name="Mesmo período", index=False)
    cp.cenarios.to_excel(xw, sheet_name=f"Cenários {a1}", index=False)
    cp.mensal.assign(competencia=cp.mensal["competencia"].astype(str)).to_excel(xw, sheet_name="Receita mensal",
                                                                               index=False)
st.download_button("Baixar comparação em Excel", buf.getvalue(), file_name=f"comparacao_anos_{c.id}.xlsx",
                   icon=":material/table:")
v.rodape()
