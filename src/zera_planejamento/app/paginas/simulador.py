"""Simulador “E se…”: mexa na receita, na folha, no pró-labore e nos custos e veja o imposto de cada regime na hora."""
import streamlit as st

from zera_planejamento.app import visual as v
from zera_planejamento.app.estado import assinatura, base_do, exigir_cliente
from zera_planejamento.calculo import ROTULO
from zera_planejamento.formatos import brl, brl_curto, comp, pct
from zera_planejamento.relatorio.graficos import COR
from zera_planejamento.simulador import Ajustes, ano_base, simular

CURTO = {"simples": "Simples", "simples_hibrido": "Simples híbrido", "presumido": "Presumido", "real": "Real"}
CHAVES = ("sim_receita", "sim_folha", "sim_custos", "sim_pro_labore")

c = exigir_cliente()
base = base_do(c)
v.cabecalho("Simulador “E se…”", f"Análise · {c.nome}",
            "Mexa nas premissas e veja na hora quanto cada regime pagaria nos próximos 12 meses — ideal para a "
            "reunião com o cliente.")
if base.receita_bruta().sum() <= 0:
    st.info("Importe os relatórios do Domínio para simular.", icon=":material/upload_file:")
    st.page_link("paginas/importar.py", label="Importar relatórios do Domínio", icon=":material/upload_file:")
    st.stop()

chave = assinatura(c, base)
cache = st.session_state.setdefault("_sim_base", {})
if chave not in cache:
    with st.spinner("Preparando os próximos 12 meses..."):
        cache.clear()
        cache[chave] = ano_base(base, c)
completa, meses = cache[chave]
pl_atual = float(completa.dados.loc[meses, "pro_labore"].fillna(0).mean())


def _voltar():
    for k in CHAVES:
        st.session_state.pop(k, None)


# ---------------- controles ----------------
with st.container(border=True):
    st.html('<div class="zera-rot" style="margin-top:0">Premissas · '
            f'{comp(meses[0])} a {comp(meses[-1])}</div>')
    a, b, d, e = st.columns(4)
    receita = a.slider("Receita", -50, 100, 0, 5, format="%d%%", key="sim_receita",
                       help="Todas as receitas; custos, compras, ICMS e ISS acompanham.")
    folha = b.slider("Folha (salários e FGTS)", -50, 100, 0, 5, format="%d%%", key="sim_folha")
    custos = d.slider("Custos e despesas", -50, 50, 0, 5, format="%d%%", key="sim_custos")
    teto = max(30_000, round(pl_atual * 3, -3))
    pro_labore = e.slider("Pró-labore mensal", 0, int(teto), int(round(pl_atual, -2)), 500, key="sim_pro_labore", format="R$ %d",
                          help="Total dos sócios por mês.")
    st.button("Voltar ao cenário base", icon=":material/restart_alt:", on_click=_voltar)

aj = Ajustes(receita / 100, folha / 100, custos / 100,
             None if abs(pro_labore - round(pl_atual, -2)) < 1 else float(pro_labore))
r = simular(completa, meses, c, aj)
rb, rs = r["base"], r["simulado"]
vb, vs = rb[rb["elegivel"]], rs[rs["elegivel"]]
melhor_b = vb["tributos"].idxmin() if not vb.empty else None
melhor_s = vs["tributos"].idxmin() if not vs.empty else None
atual = {"simples": "simples", "presumido": "presumido", "real": "real"}.get(c.regime_atual)

# ---------------- resultado ----------------
if melhor_s is None:
    st.warning("Nenhum regime calculável com esses ajustes.")
    st.stop()
mexeu = aj != Ajustes()
if mexeu and melhor_s != melhor_b:
    v.faixa(f"O menor custo passa a ser o {ROTULO[melhor_s]}",
            f"Antes dos ajustes era o {ROTULO[melhor_b]}. Diferença para o 2º colocado: "
            f"{brl(vs['tributos'].nsmallest(2).diff().iloc[-1], 0) if len(vs) > 1 else '–'} em 12 meses.",
            "Mudou")
else:
    v.faixa(f"{ROTULO[melhor_s]}: menor custo{' com esses ajustes' if mexeu else ''}",
            f"{brl(vs.at[melhor_s, 'tributos'], 0)} em 12 meses, {pct(vs.at[melhor_s, 'carga'], 1)} da receita."
            + ("" if mexeu else " Mova os controles para simular."), "Simulação" if mexeu else "Cenário base")

dif_rec = r["receita_simulado"] - r["receita_base"]
cart = [{"l": "Receita em 12 meses", "v": brl_curto(r["receita_simulado"]),
         "d": v.chip(dif_rec, f"{'+' if dif_rec >= 0 else '−'}{brl_curto(abs(dif_rec))}", bom_se_cair=False)
         if mexeu else "projeção do cenário base"},
        {"l": "Menor custo", "v": CURTO[melhor_s], "d": f"{brl_curto(vs.at[melhor_s, 'tributos'])} em 12 meses",
         "escuro": True}]
if atual in vs.index and melhor_s != atual:
    cart.append({"l": f"Economia vs. {CURTO[atual]}", "v": brl_curto(vs.at[atual, "tributos"] - vs.at[melhor_s, "tributos"]),
                 "d": "regime atual do cadastro"})
if r["fator_r_simulado"] is not None and c.anexo_servico == "fator_r":
    fr0, fr1 = r["fator_r_base"], r["fator_r_simulado"]
    cart.append({"l": "Fator R", "v": pct(fr1, 1),
                 "d": ("Anexo III" if fr1 >= 0.28 else "Anexo V") + (f" · antes {pct(fr0, 1)}" if mexeu else "")})
v.kpis(cart)

v.rotulo("Imposto em 12 meses · barra = simulado, tracejado = cenário base")
linhas = []
for reg in vs.sort_values("tributos").index:
    t0 = float(vb.at[reg, "tributos"]) if reg in vb.index else float("nan")
    t1 = float(vs.at[reg, "tributos"])
    delta = t1 - t0 if t0 == t0 else 0.0
    linhas.append({"nome": ROTULO[reg], "base": t0 if t0 == t0 else 0.0, "sim": t1, "cor": COR[reg],
                   "destaque": reg == melhor_s, "valor": brl(t1, 0),
                   "chip": v.chip(delta, ("sem mudança" if abs(delta) < 0.5 else
                                         f"{'+' if delta > 0 else '−'}{brl_curto(abs(delta))}")) if mexeu else ""})
v.corrida(linhas)
st.caption("Os ajustes valem só para os meses projetados; o histórico continua real, por isso a RBT12 e o Fator R "
           "mudam aos poucos, como na vida real. Cálculo pelo mesmo motor do planejamento.")
v.rodape()
