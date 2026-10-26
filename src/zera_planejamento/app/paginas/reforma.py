"""Reforma Tributária 2026–2033: o cliente ano a ano, com sensibilidade às alíquotas e ao regime diferenciado."""
import io

import altair as alt
import pandas as pd
import streamlit as st

from zera_planejamento.app import visual as v
from zera_planejamento.app.estado import assinatura, base_do, exigir_cliente, md, tabela_brl
from zera_planejamento.calculo import ROTULO
from zera_planejamento.formatos import brl, brl_curto, pct
from zera_planejamento.relatorio.graficos import COR
from zera_planejamento.transicao import indicadores, simular_reforma

CURTO = {"simples": "Simples", "simples_hibrido": "Simples híbrido", "presumido": "Presumido", "real": "Real"}
REDUCOES = {0.0: "Sem redução", 0.3: "30% — profissões intelectuais regulamentadas",
            0.6: "60% — saúde, educação e outros", 1.0: "Alíquota zero"}
COR_TRIBUTO = {"DAS": "#C5A15F", "DAS sem CBS/IBS": "#C5A15F", "CPP fora do DAS": "#111111", "ICMS fora do DAS": "#8C8C8C",
               "ISS fora do DAS": "#B5B5B5", "CBS por fora": "#2E8B6E", "IBS por fora": "#7CC4A8", "PIS": "#2F6EA8",
               "Cofins": "#7FA8D1", "CBS": "#2E8B6E", "IBS": "#7CC4A8", "IRPJ": "#A23E55", "CSLL": "#D78A9C",
               "ICMS": "#8C8C8C", "ISS": "#B5B5B5", "INSS patronal + RAT + Terceiros": "#111111"}

c = exigir_cliente()
base = base_do(c)
v.cabecalho("Reforma Tributária 2026–2033", f"Análise · {c.nome}",
            "Os mesmos 12 meses do cliente sob as regras de cada ano da transição: PIS/Cofins viram CBS, ICMS/ISS viram "
            "IBS. EC 132/2023 e LC 214/2025.")
if base.receita_bruta().sum() <= 0:
    st.info("Importe os relatórios do Domínio para simular a Reforma.", icon=":material/upload_file:")
    st.page_link("paginas/importar.py", label="Importar relatórios do Domínio", icon=":material/upload_file:")
    st.stop()

rr = c.regras_reforma()
with st.container(border=True):
    st.html('<div class="zera-rot" style="margin-top:0">Premissas da Reforma · ajuste para ver a sensibilidade</div>')
    a, b, d = st.columns([1, 1, 1.4])
    cbs = a.slider("CBS — alíquota de referência", 7.0, 11.0, round(rr.cbs_referencia * 100, 2), 0.05, format="%.2f%%",
                   help="[CONFERIR] O Senado fixa a de 2027 até 15/12/2026. Padrão 9,21%.") / 100
    ibs = b.slider("IBS — alíquota de referência", 14.0, 21.0, round(rr.ibs_referencia * 100, 2), 0.05, format="%.2f%%",
                   help="[CONFERIR] Estimativa; a soma CBS + IBS de referência fica perto de 28%.") / 100
    opcoes = list(REDUCOES)
    reducao = d.selectbox("Regime diferenciado do IBS/CBS (LC 214/2025)", opcoes,
                          index=opcoes.index(rr.reducao_aliquota) if rr.reducao_aliquota in opcoes else 0,
                          format_func=REDUCOES.get,
                          help="Redução das alíquotas sobre as vendas; o crédito das compras continua cheio. "
                               "[CONFERIR] se a atividade do cliente se enquadra e os requisitos.")
    mudou = (round(cbs, 6), round(ibs, 6), reducao) != (round(rr.cbs_referencia, 6), round(rr.ibs_referencia, 6),
                                                        rr.reducao_aliquota)
    if mudou and st.button("Salvar estas premissas no cadastro do cliente", icon=":material/save:"):
        c.reforma = {**c.reforma, "cbs_referencia": cbs, "ibs_referencia": ibs, "reducao_aliquota": reducao}
        c.salvar()
        st.success("Premissas salvas: o planejamento, o dashboard e os relatórios passam a usá-las.",
                   icon=":material/check:")

chave = (assinatura(c, base), cbs, ibs, reducao)
cache = st.session_state.setdefault("_reforma", {})
if chave not in cache:
    with st.spinner("Aplicando as regras de 2026 a 2033..."):
        cache.clear()
        cache[chave] = simular_reforma(base, c, cbs, ibs, reducao)
rf = cache[chave]
ind = indicadores(rf)
regs = list(rf.carga.columns)

# ---------------- leitura ----------------
m26, m33 = ind.get("melhor_2026"), ind.get("melhor_2033")
if ind["anos_de_virada"]:
    v.faixa(f"A Reforma muda o regime de menor carga em {ind['anos_de_virada'][0]}",
            f"Hoje: {ROTULO[m26]}. Em 2033: {ROTULO[m33]}. Planeje a troca para o início do ano da virada "
            "(a opção de regime é anual).", "Atenção")
else:
    v.faixa(f"{ROTULO[m33]}: menor carga em todos os anos até 2033",
            f"Base: {rf.periodo_base}. A ordem dos regimes não muda na transição com estas premissas.", "Reforma")
cart = []
if "atual_2026" in ind:
    var = ind["variacao_atual"]
    cart.append({"l": f"{CURTO[rf.atual]} 2026 → 2033", "v": f"{'+' if var >= 0 else ''}{pct(var, 1)}",
                 "d": f"{brl_curto(ind['atual_2026'])} → {brl_curto(ind['atual_2033'])}", "escuro": True})
if "mais_sobe" in ind:
    cart.append({"l": "Regime que mais sobe", "v": CURTO[ind["mais_sobe"]],
                 "d": v.variacao(ind["mais_sobe_var"], f"{pct(ind['mais_sobe_var'], 0)} até 2033", bom_se_positivo=False)})
if "ganho_acumulado" in ind:
    cart.append({"l": "Ganho de escolher o melhor", "v": brl_curto(ind["ganho_acumulado"]),
                 "d": "2027–2033, contra ficar no regime atual"})
receita = rf.anual["receita"].iloc[0]
cart.append({"l": "Receita-base (12 meses)", "v": brl_curto(receita), "d": rf.periodo_base})
v.kpis(cart)

# ---------------- gráficos ----------------
escala = alt.Scale(domain=[ROTULO[r] for r in COR], range=list(COR.values()))
EIXO_RS = alt.Axis(labelExpr="'R$ ' + format(datum.value / 1000, ',.0f') + ' mil'", title=None)
t = rf.anual[regs].reset_index().melt("ano", var_name="regime", value_name="tributos").dropna()
t["Regime"], t["valor"] = t["regime"].map(ROTULO), t["tributos"].map(lambda x: brl(x, 0))
t["carga"] = [pct(rf.carga.at[a, r], 1) for a, r in zip(t["ano"], t["regime"])]
sel = alt.selection_point(fields=["Regime"], bind="legend")
ESCALA_ANO = alt.Scale(domain=[2025.5, 2033.5], zero=False, nice=False)
faixa_teste = alt.Chart(pd.DataFrame({"a": [2025.6], "b": [2026.4]})).mark_rect(color=v.CREME).encode(
    x=alt.X("a:Q", scale=ESCALA_ANO), x2="b:Q")
faixa_icms = alt.Chart(pd.DataFrame({"a": [2028.6], "b": [2032.4]})).mark_rect(color="#F3F6F2").encode(
    x=alt.X("a:Q", scale=ESCALA_ANO), x2="b:Q")
notas = alt.Chart(pd.DataFrame({"x": [2026, 2030.5], "t": ["TESTE", "ICMS/ISS → IBS"]})).mark_text(
    dy=-4, fontSize=9, fontWeight="bold", color=v.DOURADO_TXT, font="Inter", baseline="top").encode(
    x=alt.X("x:Q", scale=ESCALA_ANO), y=alt.value(0), text="t:N")
linhas = alt.Chart(t).mark_line(point=alt.OverlayMarkDef(size=70, filled=True), strokeWidth=2.6).encode(
    x=alt.X("ano:Q", title=None, scale=alt.Scale(domain=[2025.5, 2033.5], zero=False, nice=False),
            axis=alt.Axis(format="d", values=list(range(2026, 2034)), labelFontSize=12)),
    y=alt.Y("tributos:Q", axis=EIXO_RS), color=alt.Color("Regime:N", scale=escala, title=None),
    opacity=alt.condition(sel, alt.value(1), alt.value(0.12)),
    tooltip=[alt.Tooltip("ano:Q", title="Ano"), "Regime", alt.Tooltip("valor:N", title="Tributos"),
             alt.Tooltip("carga:N", title="Carga")]).add_params(sel)
v.rotulo("Tributos por ano e regime")
st.altair_chart(v.grafico(alt.layer(faixa_teste, faixa_icms, notas, linhas), altura=340), width="stretch")
st.caption("Clique num regime da legenda para isolá-lo. Faixa dourada: ano de teste; faixa verde: troca gradual do "
           "ICMS/ISS pelo IBS.")

a, b = st.columns([1.3, 1])
with a:
    v.rotulo("Composição ano a ano")
    reg_comp = st.segmented_control("Regime", regs, default=rf.atual if rf.atual in regs else regs[0],
                                    format_func=CURTO.get, key="reforma_regime") or regs[0]
    cp = rf.composicao[rf.composicao.regime == reg_comp].copy()
    cp["valor_txt"] = cp["valor"].map(lambda x: brl(x, 0))
    ordem = list(dict.fromkeys(cp["tributo"]))
    pilha = alt.Chart(cp).mark_bar(size=30, cornerRadiusEnd=2).encode(
        x=alt.X("ano:O", title=None, axis=alt.Axis(labelAngle=0)), y=alt.Y("sum(valor):Q", axis=EIXO_RS),
        color=alt.Color("tributo:N", title=None, sort=ordem,
                        scale=alt.Scale(domain=ordem, range=[COR_TRIBUTO.get(x, "#999") for x in ordem]),
                        legend=alt.Legend(columns=3, labelLimit=180)),
        order=alt.Order("tributo:N"),
        tooltip=[alt.Tooltip("ano:O", title="Ano"), alt.Tooltip("tributo:N", title="Tributo"),
                 alt.Tooltip("valor_txt:N", title="Valor")])
    st.altair_chart(v.grafico(pilha, altura=330), width="stretch")
with b:
    v.rotulo("Cronograma da transição")
    cr = rf.cronograma
    v.prazos_html([(str(ano), "CBS 0,9% · IBS 0,1% (teste)" if ano == 2026 else f"CBS {pct(r.cbs, 2)} · IBS {pct(r.ibs, 2)}",
                    "PIS/COFINS" if r.pis_cofins else ("ICMS/ISS " + pct(r.icms_iss, 0) if r.icms_iss > 0 else "IBS PLENO"),
                    r.marco) for ano, r in cr.iterrows()])

# ---------------- tabela ----------------
v.rotulo("Tributos e carga por ano")
tab = rf.anual.copy()
for r in regs:
    tab[f"Carga {CURTO[r]}"] = rf.carga[r].values
tab["Menor carga"] = rf.melhor.map(CURTO)
tab = tab.rename(columns={"receita": "Receita", **{r: CURTO[r] for r in regs}})
tab.index = tab.index.astype(str)
st.dataframe(tabela_brl(tab.reset_index().rename(columns={"ano": "Ano"}),
                        tuple(f"Carga {CURTO[r]}" for r in regs)), hide_index=True, width="stretch")
for o in rf.observacoes:
    st.caption(md(o))
st.caption("Premissas: mesma operação e mesmo preço sem tributos dos últimos 12 meses; CBS/IBS cobrados por fora; "
           "créditos de CBS/IBS sobre as compras com nota (insumos, energia, aluguel, serviços, fretes, uso e consumo e "
           "imobilizado). Alíquotas de referência são estimativas [CONFERIR].")

buf = io.BytesIO()
with pd.ExcelWriter(buf, engine="openpyxl") as xw:
    rf.anual.to_excel(xw, sheet_name="Tributos por ano")
    rf.carga.to_excel(xw, sheet_name="Carga por ano")
    rf.composicao.to_excel(xw, sheet_name="Composição", index=False)
    rf.cronograma.to_excel(xw, sheet_name="Cronograma")
st.download_button("Baixar a simulação da Reforma em Excel", buf.getvalue(), file_name=f"reforma_{c.id}.xlsx",
                   icon=":material/table:")
v.rodape()
