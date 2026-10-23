"""Dashboard do cliente: recomendação, indicadores e gráficos interativos por cenário e período."""
import altair as alt
import pandas as pd
import streamlit as st

from zera_planejamento.app import visual as v
from zera_planejamento.app.estado import base_do, exigir_cliente, planejamento_do
from zera_planejamento.calculo import ROTULO
from zera_planejamento.formatos import brl, brl_curto, comp, pct
from zera_planejamento.painel import PERIODOS, montar_painel
from zera_planejamento.projecao import CENARIOS
from zera_planejamento.relatorio.graficos import COR

CURTO = {"simples": "Simples", "simples_hibrido": "Simples híbrido", "presumido": "Presumido", "real": "Real"}
# cores por família de tributo (sem depender só de tons de dourado)
COR_TRIBUTO = {"DAS": "#C5A15F", "DAS sem CBS/IBS": "#C5A15F", "CPP fora do DAS": "#111111",
               "ICMS fora do DAS": "#8C8C8C", "ISS fora do DAS": "#B5B5B5", "CBS por fora": "#2E8B6E",
               "IBS por fora": "#7CC4A8", "PIS": "#2F6EA8", "Cofins": "#7FA8D1", "CBS": "#2E8B6E", "IBS": "#7CC4A8",
               "IRPJ": "#A23E55", "CSLL": "#D78A9C", "ICMS": "#8C8C8C", "ISS": "#B5B5B5",
               "INSS patronal + RAT + Terceiros": "#111111"}
MES_PT = ("['jan','fev','mar','abr','mai','jun','jul','ago','set','out','nov','dez'][month(datum.value)]"
          " + '/' + timeFormat(datum.value, '%y')")
EIXO_MES = alt.Axis(labelExpr=MES_PT, labelAngle=0, title=None, tickCount="month")

c = exigir_cliente()
base = base_do(c)
v.cabecalho(c.nome, "Dashboard · planejamento tributário",
            f"CNPJ {c.cnpj or '–'} · regime atual: {ROTULO.get(c.regime_atual, c.regime_atual)}")
try:
    pl = planejamento_do(c, base)
except ValueError as erro:
    st.info(str(erro), icon=":material/upload_file:")
    st.stop()

mh, mp = pl.meses_historico, pl.meses_projetados
st.caption(f"Histórico {comp(mh[0])} a {comp(mh[-1])} · projeção {comp(mp[0])} a {comp(mp[-1])} · rascunho técnico "
           "para revisão do contador")

# ---------------- filtros ----------------
f1, f2, f3 = st.columns([1.35, 1.5, 1.9])
cenario = f1.segmented_control("Cenário", CENARIOS, default="Neutro", key="dash_cenario") or "Neutro"
periodo = f2.segmented_control("Período", list(PERIODOS), default="projecao", key="dash_periodo",
                               format_func={"projecao": f"Próximos {len(mp)} meses", "historico": "Últimos 12 meses"}.get)
periodo = periodo or "projecao"
p = montar_painel(pl, cenario, periodo)
disponiveis = list(p.ranking["regime"])
visiveis = f3.pills("Regimes nos gráficos", disponiveis, default=disponiveis, selection_mode="multi",
                    format_func=CURTO.get, key="dash_regimes")
visiveis = visiveis or disponiveis
ind = p.indicadores
rotulos_vis = [ROTULO[r] for r in visiveis]
escala = alt.Scale(domain=[ROTULO[r] for r in COR], range=list(COR.values()))
EIXO_RS = alt.Axis(labelExpr="'R$ ' + format(datum.value / 1000, ',.0f') + ' mil'", title=None)
qual = "projetados" if periodo == "projecao" else "do histórico"

# ---------------- recomendação ----------------
if "recomendado" in ind:
    prazo = f" Decidir até {ind['prazo_data']:%d/%m/%Y} ({ind['prazo_dias']} dias)." if ind.get("prazo_acao") == "DECIDIR" else ""
    if ind["mudar"] and "economia_ano" in ind:
        v.faixa(f"Mudar para {ind['rotulo_recomendado']}",
                f"Economia estimada de {brl(ind['economia_ano'], 0)} por ano em relação ao {ind['rotulo_atual']} "
                f"(cenário {cenario}, {p.indicadores['n_meses']} meses {qual}).{prazo}", "Recomendação")
    elif ind["mudar"]:
        v.faixa(f"Menor carga: {ind['rotulo_recomendado']}",
                f"O regime atual não é calculável com os dados; confira o cadastro.{prazo}", "Atenção")
    else:
        extra = (f" Vantagem de {brl(ind['vantagem_segundo'], 0)} ({pct(ind['vantagem_segundo_pct'], 1)}) sobre o "
                 f"{ind['segundo']}." if "segundo" in ind else "")
        v.faixa(f"Manter o {ind['rotulo_recomendado']}", f"O regime atual já é o de menor carga no cenário {cenario}."
                + extra, "Recomendação")

# ---------------- indicadores ----------------
cart = []
if "recomendado" in ind:
    cart.append({"l": "Menor carga", "v": CURTO[ind["recomendado"]],
                 "d": f"{brl_curto(ind['tributos_recomendado'])} em {ind['n_meses']} meses", "escuro": True})
if "economia_ano" in ind:
    cart.append({"l": "Economia por ano", "v": brl_curto(max(ind["economia_ano"], 0)),
                 "d": "mantendo o regime atual" if not ind["mudar"] else v.variacao(1, f"vs. {ind['rotulo_atual']}")})
if "carga_recomendado" in ind:
    d = (v.variacao(ind["carga_atual"] - ind["carga_recomendado"], f"atual {pct(ind['carga_atual'], 1)}")
         if "carga_atual" in ind and ind["mudar"] else "sobre a receita do período")
    cart.append({"l": "Carga efetiva", "v": pct(ind["carga_recomendado"], 2), "d": d})
cres = ind.get("crescimento")
cart.append({"l": "Receita no período", "v": brl_curto(ind["receita_periodo"]),
             "d": v.variacao(cres, f"{pct(cres, 1)} média mensal projetada") if cres == cres and periodo == "projecao"
             else f"12 meses: {brl_curto(ind['receita_12m'])}"})
if "fator_r" in ind:
    fr = ind["fator_r"]
    cart.append({"l": "Fator R atual", "v": pct(fr, 1),
                 "d": v.variacao(fr - 0.28, "Anexo III" if fr >= 0.28 else f"Anexo V — faltam {pct(0.28 - fr, 1)}")})
elif "segundo" in ind:
    cart.append({"l": "Vantagem sobre o 2º", "v": pct(ind["vantagem_segundo_pct"], 1),
                 "d": f"{brl(ind['vantagem_segundo'], 0)} vs. {ind['segundo'].replace(' (IBS/CBS por fora)', '')}"})
if "prazo_data" in ind:
    cart.append({"l": "Próximo prazo", "v": f"{ind['prazo_data']:%d/%m/%Y}",
                 "d": f"em {ind['prazo_dias']} dias · {ind['prazo_acao'].lower()}"})
v.kpis(cart)
al = ind["alertas"]
if al["CRÍTICO"]:
    st.error(f"{al['CRÍTICO']} alerta(s) crítico(s): revise a base antes de usar estes números (detalhes abaixo).",
             icon=":material/error:")
if ind.get("socios_muda"):
    st.info(f"Somando a retirada dos sócios (Lei 15.270/2025), a menor carga total passa a ser o {ind['socios_melhor']}. "
            "Veja *Sócios e pró-labore*.".replace("$", r"\$"), icon=":material/group:")

# ---------------- comparativo ----------------
v.rotulo(f"Comparativo dos regimes · cenário {cenario}")
a, b = st.columns([1, 1.15])
rk = p.ranking[p.ranking.regime.isin(visiveis)].copy()
rk["valor"] = rk["tributos"].map(lambda x: brl(x, 0))
rk["carga_txt"] = rk["carga"].map(lambda x: pct(x, 1))
rk["destaque"] = rk["melhor"].map({True: "Menor carga", False: ""}) + rk["atual"].map({True: " · atual", False: ""})
barras = alt.Chart(rk).mark_bar(cornerRadiusEnd=4, height=26).encode(
    y=alt.Y("rotulo:N", sort=list(rk.sort_values("tributos")["rotulo"]), title=None,
            axis=alt.Axis(labelLimit=220, labelFontSize=12, labelColor=v.TEXTO)),
    x=alt.X("tributos:Q", axis=EIXO_RS),
    color=alt.Color("rotulo:N", scale=escala, legend=None),
    opacity=alt.condition("datum.melhor", alt.value(1.0), alt.value(0.55)),
    tooltip=[alt.Tooltip("rotulo:N", title="Regime"), alt.Tooltip("valor:N", title="Tributos"),
             alt.Tooltip("carga_txt:N", title="Carga"), alt.Tooltip("destaque:N", title=" ")])
texto = barras.mark_text(align="left", dx=6, fontSize=12, font="Inter", color=v.TEXTO).encode(
    text=alt.Text("valor:N"), opacity=alt.value(1))
with a:
    st.markdown("**Tributos no período por regime**")
    st.altair_chart(v.grafico(barras + texto, altura=max(150, 60 * len(rk))), width="stretch")
    st.caption("Barra cheia = menor carga. Passe o mouse para ver a carga efetiva.")

comp_df = p.composicao[p.composicao.regime.isin(visiveis)].copy()
if not comp_df.empty:
    comp_df["valor_txt"] = comp_df["valor"].map(brl)
    comp_df["curto"] = comp_df["regime"].map(CURTO)
    trib = list(dict.fromkeys(comp_df["tributo"]))
    sel = alt.selection_point(fields=["tributo"], bind="legend")
    empilhado = alt.Chart(comp_df).mark_bar(cornerRadiusEnd=2).encode(
        x=alt.X("curto:N", title=None, sort=[CURTO[r] for r in rk.sort_values("tributos")["regime"]],
                axis=alt.Axis(labelAngle=0, labelFontSize=12, labelColor=v.TEXTO)),
        y=alt.Y("sum(valor):Q", axis=EIXO_RS),
        color=alt.Color("tributo:N", title=None, scale=alt.Scale(domain=trib, range=[COR_TRIBUTO.get(t, "#999") for t in trib]),
                        legend=alt.Legend(columns=3, symbolLimit=20, labelLimit=200)),
        opacity=alt.condition(sel, alt.value(1), alt.value(0.2)),
        tooltip=[alt.Tooltip("rotulo:N", title="Regime"), alt.Tooltip("tributo:N", title="Tributo"),
                 alt.Tooltip("valor_txt:N", title="Valor")]).add_params(sel)
    with b:
        st.markdown("**Composição por tributo**")
        st.altair_chart(v.grafico(empilhado, altura=300), width="stretch")
        st.caption("Clique num tributo da legenda para destacá-lo.")

# ---------------- evolução mensal ----------------
v.rotulo("Evolução mês a mês · histórico e projeção")
ms = p.mensal[p.mensal.regime.isin(visiveis)].copy()
ms["valor_txt"] = ms["tributos"].map(brl)
ms["mes_txt"] = ms["competencia"].map(comp)
inicio_proj = pd.Period(mp[0], "M").to_timestamp()
fim_proj = pd.Period(mp[-1], "M").to_timestamp()
faixa_proj = alt.Chart(pd.DataFrame({"i": [inicio_proj], "f": [fim_proj], "t": [f"Projeção · {cenario}"]})).mark_rect(
    color=v.CREME, opacity=0.9).encode(x="i:T", x2="f:T")
rotulo_proj = alt.Chart(pd.DataFrame({"i": [inicio_proj], "t": [f"PROJEÇÃO · {cenario.upper()}"]})).mark_text(
    align="left", baseline="top", dx=6, dy=4, fontSize=10, fontWeight="bold", color=v.DOURADO_TXT, font="Inter").encode(
    x="i:T", y=alt.value(0), text="t:N")
legenda = alt.selection_point(fields=["rotulo"], bind="legend")
perto = alt.selection_point(nearest=True, on="pointerover", fields=["mes"], empty=False)
linhas = alt.Chart(ms).mark_line(strokeWidth=2.4, interpolate="monotone").encode(
    x=alt.X("mes:T", axis=EIXO_MES),
    y=alt.Y("tributos:Q", axis=EIXO_RS),
    color=alt.Color("rotulo:N", title=None, scale=escala),
    strokeDash=alt.StrokeDash("fase:N", scale=alt.Scale(domain=["Histórico", "Projeção"], range=[[1, 0], [6, 4]]),
                              legend=None),
    opacity=alt.condition(legenda, alt.value(1), alt.value(0.12)), detail="fase:N").add_params(legenda)
pontos = linhas.mark_point(filled=True, size=70).encode(
    opacity=alt.condition(perto, alt.value(1), alt.value(0)),
    tooltip=[alt.Tooltip("mes_txt:N", title="Mês"), alt.Tooltip("rotulo:N", title="Regime"),
             alt.Tooltip("valor_txt:N", title="Tributos"), alt.Tooltip("fase:N", title="Fase")]).add_params(perto)
regua = alt.Chart(ms).mark_rule(color="#BDB3A0", strokeDash=[2, 3]).encode(x="mes:T").transform_filter(perto)
st.altair_chart(v.grafico(alt.layer(faixa_proj, rotulo_proj, linhas, pontos, regua), altura=340), width="stretch")
st.caption("Linha cheia = histórico; tracejada = projeção. Clique num regime da legenda para isolá-lo.")

# ---------------- receita e carga ----------------
a, b = st.columns([1.6, 1]) if not p.fator_r.empty else (st.container(), None)
rc = p.receita.copy()
rc["receita_txt"] = rc["receita"].map(lambda x: brl(x, 0))
rc["carga_txt"] = rc["carga_recomendado"].map(lambda x: pct(x, 2))
rc["mes_txt"] = rc["competencia"].map(comp)
base_rc = alt.Chart(rc).encode(x=alt.X("mes:T", axis=EIXO_MES))
col_rec = base_rc.mark_bar(cornerRadiusEnd=3, size=16).encode(
    y=alt.Y("receita:Q", axis=alt.Axis(labelExpr="'R$ ' + format(datum.value / 1000, ',.0f') + ' mil'",
                                       title="Receita", titleColor=v.CINZA)),
    color=alt.Color("fase:N", scale=alt.Scale(domain=["Histórico", "Projeção"], range=["#D9C49A", "#EFE4CC"]),
                    title=None),
    tooltip=[alt.Tooltip("mes_txt:N", title="Mês"), alt.Tooltip("receita_txt:N", title="Receita"),
             alt.Tooltip("carga_txt:N", title="Carga (menor regime)")])
lin_carga = base_rc.mark_line(color=v.PRETO, strokeWidth=2, point=alt.OverlayMarkDef(color=v.PRETO, size=30)).encode(
    y=alt.Y("carga_recomendado:Q", axis=alt.Axis(format=".0%", title=f"Carga — {ind.get('rotulo_recomendado', '')}",
                                                titleColor=v.CINZA)),
    tooltip=[alt.Tooltip("mes_txt:N", title="Mês"), alt.Tooltip("carga_txt:N", title="Carga")])
with a:
    v.rotulo("Receita e carga efetiva do regime de menor carga")
    st.altair_chart(v.grafico(alt.layer(col_rec, lin_carga).resolve_scale(y="independent"), altura=280), width="stretch")
if b is not None:
    fr_df = p.fator_r.copy()
    fr_df["txt"] = fr_df["fator_r"].map(lambda x: pct(x, 1))
    fr_df["mes_txt"] = fr_df["competencia"].map(comp)
    corte = alt.Chart(pd.DataFrame({"y": [0.28]})).mark_rule(color=v.DOURADO, strokeWidth=2, strokeDash=[5, 3]).encode(y="y:Q")
    corte_txt = alt.Chart(pd.DataFrame({"y": [0.28], "t": ["28% → Anexo III"]})).mark_text(
        align="left", dx=4, dy=-7, fontSize=10, color=v.DOURADO_TXT, font="Inter", fontWeight="bold").encode(
        y="y:Q", x=alt.value(0), text="t:N")
    lfr = alt.Chart(fr_df).mark_line(color=v.PRETO, strokeWidth=2, point=alt.OverlayMarkDef(color=v.PRETO)).encode(
        x=alt.X("mes:T", axis=EIXO_MES),
        y=alt.Y("fator_r:Q", axis=alt.Axis(format=".0%", title=None)),
        strokeDash=alt.StrokeDash("fase:N", scale=alt.Scale(domain=["Histórico", "Projeção"], range=[[1, 0], [6, 4]]),
                                  legend=None),
        tooltip=[alt.Tooltip("mes_txt:N", title="Mês"), alt.Tooltip("txt:N", title="Fator R"), "fase:N"])
    with b:
        v.rotulo("Fator R (folha ÷ receita, 12 meses)")
        st.altair_chart(v.grafico(alt.layer(corte, corte_txt, lfr), altura=280), width="stretch")

# ---------------- transição ----------------
if pl.transicao is not None and not pl.transicao.empty:
    v.rotulo("Transição da Reforma · 2026 a 2033")
    t = pl.transicao.drop(columns="receita").reset_index().melt("ano", var_name="regime", value_name="tributos").dropna()
    t = t[t.regime.isin(visiveis)]
    t["Regime"] = t["regime"].map(ROTULO)
    t["valor_txt"] = t["tributos"].map(lambda x: brl(x, 0))
    sel_t = alt.selection_point(fields=["Regime"], bind="legend")
    tr = alt.Chart(t).mark_line(point=alt.OverlayMarkDef(size=60, filled=True), strokeWidth=2.2).encode(
        x=alt.X("ano:O", title=None, axis=alt.Axis(labelAngle=0)), y=alt.Y("tributos:Q", axis=EIXO_RS),
        color=alt.Color("Regime:N", title=None, scale=escala),
        opacity=alt.condition(sel_t, alt.value(1), alt.value(0.12)),
        tooltip=[alt.Tooltip("ano:O", title="Ano"), "Regime", alt.Tooltip("valor_txt:N", title="Tributos no ano")]
    ).add_params(sel_t)
    st.altair_chart(v.grafico(tr, altura=260), width="stretch")
    st.caption("Últimos 12 meses sob a regra de cada ano. CBS/IBS de referência estimadas (editáveis no cadastro).")

# ---------------- prazos e alertas ----------------
a, b = st.columns([1.2, 1])
with a:
    v.rotulo("Prazos de decisão")
    if pl.prazos is not None and not pl.prazos.empty:
        v.prazos_html([(f"{z.data:%d/%m/%Y}", f"em {z.dias} dias", z.acao, z.evento) for z in pl.prazos.itertuples()])
with b:
    v.rotulo("Alertas da análise")
    st.html("".join(
        f'<span class="zera-selo" style="background:{cor};color:{txt}">{n}: {al[n]}</span>'
        for n, cor, txt in (("CRÍTICO", v.VINHO, "#fff"), ("ATENÇÃO", v.DOURADO, v.PRETO), ("INFO", v.CREME, v.CINZA))))
    df_al = pl.alertas.como_df()
    for row in df_al[df_al.nivel != "INFO"].head(6).itertuples():
        (st.error if row.nivel == "CRÍTICO" else st.warning)(f"**{row.origem}** — {row.mensagem}".replace("$", r"\$"))
    if len(df_al):
        with st.expander(f"Todos os alertas ({len(df_al)})"):
            for row in df_al.itertuples():
                st.markdown(f"- **{row.nivel} · {row.origem}** — {row.mensagem}".replace("$", r"\$"))
v.rodape()
