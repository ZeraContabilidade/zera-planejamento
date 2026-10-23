"""
Dados do dashboard do cliente, montados a partir de um ``Planejamento`` já calculado.

Nada é recalculado aqui: o painel só recorta e organiza os números do motor por cenário
(Neutro, Otimista, Pessimista) e por período (meses projetados ou últimos 12 meses do histórico).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .calculo import COMPONENTES, NOME_TRIBUTO, ROTULO
from .planejamento import Planejamento

REGIME_DO_CADASTRO = {"simples": "simples", "presumido": "presumido", "real": "real"}
PERIODOS = {"projecao": "Próximos meses (projeção)", "historico": "Últimos 12 meses (histórico)"}


@dataclass
class Painel:
    cenario: str
    periodo: str
    meses: pd.PeriodIndex
    ranking: pd.DataFrame          # regime × tributos/carga no período
    mensal: pd.DataFrame           # formato longo: competência × regime, histórico + projeção
    receita: pd.DataFrame          # competência, receita, fase, carga do recomendado e do atual
    composicao: pd.DataFrame       # regime × tributo no período
    fator_r: pd.DataFrame          # competência, Fator R, fase (vazio sem receita do Fator R)
    indicadores: dict = field(default_factory=dict)


def _resumo(pl: Planejamento, cenario: str, periodo: str) -> tuple[pd.DataFrame, pd.PeriodIndex]:
    if periodo == "historico":
        return pl.historico.resumo(pl.meses_historico), pl.meses_historico
    c = pl.cenarios[cenario]
    return c.resultado.resumo(c.meses), c.meses


def montar_painel(pl: Planejamento, cenario: str = "Neutro", periodo: str = "projecao") -> Painel:
    resumo, meses = _resumo(pl, cenario, periodo)
    n = len(meses)
    anual = 12 / n
    atual = REGIME_DO_CADASTRO.get(pl.cliente.regime_atual)

    # ---------------- ranking ----------------
    rk = resumo[resumo["elegivel"]].copy()
    rk["rotulo"] = [ROTULO[r] for r in rk.index]
    rk["atual"] = rk.index == atual
    rk["tributos_ano"] = rk["tributos"] * anual
    rk = rk.sort_values("tributos")
    rk["posicao"] = range(1, len(rk) + 1)
    ranking = rk[["rotulo", "tributos", "tributos_ano", "carga", "melhor", "atual", "posicao"]].reset_index()

    # ---------------- série mensal: histórico + cenário ----------------
    cen = pl.cenarios[cenario]
    hist = pl.historico.mensal().loc[pl.meses_historico].assign(fase="Histórico")
    proj = cen.resultado.mensal().loc[cen.meses].assign(fase="Projeção")
    serie = pd.concat([hist, proj])
    mensal = (serie.reset_index().melt(["competencia", "fase"], var_name="regime", value_name="tributos")
              .dropna(subset=["tributos"]))
    mensal["rotulo"] = mensal["regime"].map(ROTULO)
    mensal["mes"] = mensal["competencia"].dt.to_timestamp()

    rb = pd.concat([pl.base.receita_bruta().loc[pl.meses_historico], cen.base_completa.receita_bruta().loc[cen.meses]])
    melhor = ranking.loc[ranking["melhor"], "regime"].iloc[0] if ranking["melhor"].any() else None
    receita = pd.DataFrame({"competencia": serie.index, "receita": rb.values, "fase": serie["fase"].values})
    receita["mes"] = receita["competencia"].dt.to_timestamp()
    for nome, reg in (("carga_recomendado", melhor), ("carga_atual", atual)):
        receita[nome] = (serie[reg].values / rb.replace(0, np.nan).values) if reg in serie else np.nan

    # ---------------- composição ----------------
    linhas = []
    for reg in rk.index:
        for k in COMPONENTES[reg]:
            col = f"comp_{k}"
            if col in resumo.columns and pd.notna(resumo.at[reg, col]) and resumo.at[reg, col] > 0.005:
                linhas.append({"regime": reg, "rotulo": ROTULO[reg], "tributo": NOME_TRIBUTO[k],
                               "valor": float(resumo.at[reg, col])})
    composicao = pd.DataFrame(linhas, columns=["regime", "rotulo", "tributo", "valor"])

    # ---------------- Fator R ----------------
    fr = pd.DataFrame(columns=["competencia", "mes", "fator_r", "fase"])
    if "simples" in pl.historico.regimes and pl.base.dados["rec_fator_r"].fillna(0).sum() > 0:
        h = pl.historico.regimes["simples"].loc[pl.meses_historico, "fator_r"]
        p = cen.resultado.regimes["simples"].loc[cen.meses, "fator_r"]
        fr = pd.DataFrame({"competencia": list(h.index) + list(p.index), "fator_r": list(h.values) + list(p.values),
                           "fase": ["Histórico"] * len(h) + ["Projeção"] * len(p)})
        fr["mes"] = pd.PeriodIndex(fr["competencia"], freq="M").to_timestamp()

    # ---------------- indicadores ----------------
    ind: dict = {"n_meses": n, "atual": atual, "rotulo_atual": ROTULO.get(atual, pl.cliente.regime_atual)}
    if melhor is not None:
        m = rk.loc[melhor]
        ind.update(recomendado=melhor, rotulo_recomendado=ROTULO[melhor], tributos_recomendado=float(m["tributos"]),
                   carga_recomendado=float(m["carga"]))
        if len(rk) > 1:
            s = rk.iloc[1]
            ind.update(segundo=ROTULO[rk.index[1]], vantagem_segundo=float(s["tributos"] - m["tributos"]),
                       vantagem_segundo_pct=float((s["tributos"] - m["tributos"]) / s["tributos"]))
    if atual in rk.index:
        a = rk.loc[atual]
        ind.update(tributos_atual=float(a["tributos"]), carga_atual=float(a["carga"]))
        if melhor is not None:
            ind["economia_periodo"] = float(a["tributos"] - rk.loc[melhor, "tributos"])
            ind["economia_ano"] = ind["economia_periodo"] * anual
    ind["mudar"] = melhor is not None and melhor not in (atual, f"{atual}_hibrido") and ind.get("economia_ano", 1) > 0
    ind["receita_periodo"] = float(resumo["receita"].iloc[0]) if len(resumo) else 0.0
    rb_hist = pl.base.receita_bruta().loc[pl.meses_historico]
    ind["receita_12m"] = float(rb_hist.sum())
    media_hist = float(rb_hist.mean()) if len(rb_hist) else 0.0
    media_proj = float(cen.base_completa.receita_bruta().loc[cen.meses].mean())
    ind["receita_media_hist"], ind["receita_media_proj"] = media_hist, media_proj
    ind["crescimento"] = media_proj / media_hist - 1 if media_hist else np.nan
    if not fr.empty:
        ultimo = fr[fr["fase"] == "Histórico"].iloc[-1]
        ind["fator_r"] = float(ultimo["fator_r"])
    pz = pl.prazos if pl.prazos is not None else pd.DataFrame()
    if not pz.empty:
        decidir = pz[pz["acao"] == "DECIDIR"]
        prox = (decidir if not decidir.empty else pz).iloc[0]
        ind.update(prazo_data=prox["data"], prazo_dias=int(prox["dias"]), prazo_evento=prox["evento"],
                   prazo_acao=prox["acao"])
    ind["alertas"] = pl.alertas.contagem()
    if pl.socios is not None and not pl.socios.vazia:
        s = pl.socios.resumo[pl.socios.resumo["melhor"]].iloc[0]
        ind.update(socios_melhor=s["rotulo"], socios_carga=float(s["carga_total"]),
                   socios_muda=s.name != melhor)
    return Painel(cenario, periodo, meses, ranking, mensal, receita, composicao, fr, ind)
