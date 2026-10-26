"""
Comparação entre anos: realizado de cada ano, estimativa de fechamento do ano corrente e projeção do próximo ano.

- Anos anteriores: só meses reais da base (marcados "parcial" se faltarem meses).
- Ano corrente: meses reais + meses restantes estimados (cenário central da projeção).
- Próximo ano: 12 meses projetados, em três cenários.
- Comparação no **mesmo período**: os meses reais do ano corrente contra os mesmos meses do ano anterior
  (ex.: jan–set/2026 × jan–set/2025), que é a comparação justa quando o ano ainda não fechou.

Tudo sai do motor (``calculo.calcular``) rodando na série inteira (histórico + projeção). Assim, a RBT12, os
trimestres, o prejuízo e as regras de cada ano (CBS/IBS a partir de 2027, RBT12 sem o mês anterior) são as
mesmas do planejamento. A projeção reaproveita ``projecao.projetar``:

- "tendencia" / "media": como no cadastro, com Otimista/Pessimista = ± variação;
- "crescimento": média dos últimos 12 meses × (1 + crescimento informado), com ± variação nos cenários.
  Custos e compras acompanham a receita; folha e despesas fixas, não (mesmas premissas da projeção).
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .alertas import Alertas
from .base import BaseMensal
from .calculo import REGIMES, ROTULO
from .cliente import Cliente, Projecao
from .formatos import MESES
from .projecao import projetar

REGIME_DO_CADASTRO = {"simples": "simples", "presumido": "presumido", "real": "real"}
INICIO_HIBRIDO = 2027              # LC 214/2025: opção do Simples pelo IBS/CBS por fora
METODOS = {"tendencia": "Tendência dos últimos 12 meses", "media": "Média dos últimos 12 meses",
           "crescimento": "Média + crescimento informado"}


@dataclass
class ComparativoAnual:
    ano_atual: int
    proximo_ano: int
    anos: pd.DataFrame                 # uma linha por ano
    mesmo_periodo: pd.DataFrame        # meses reais do ano atual × mesmos meses do ano anterior (vazio se não houver)
    periodo_txt: str                   # ex.: "jan–set"
    mensal: pd.DataFrame               # ano, mês, receita, tipo (real/estimado/projetado)
    cenarios: pd.DataFrame             # cenário × regime no próximo ano
    crescimento_observado: float | None
    metodo: str
    alertas: Alertas = field(default_factory=Alertas)


def _tem_dre(base: BaseMensal, meses) -> bool:
    d = base.dados.reindex(pd.PeriodIndex(list(meses), freq="M"))
    return bool(d[["custos", "despesas"]].notna().any().any())


def _cenarios(base: BaseMensal, cliente: Cliente, meses: int, metodo: str, crescimento: float, variacao: float,
              alertas: Alertas) -> dict[str, object]:
    """Resultados do motor (série completa) por cenário: Pessimista, Central, Otimista."""
    proj = cliente.projecao

    def rodar(met, otim, pess):
        cli = dataclasses.replace(cliente, projecao=Projecao(meses=meses, janela=12, metodo=met, otimista=otim,
                                                             pessimista=pess, sazonalidade=proj.sazonalidade))
        return projetar(base, cli, alertas)

    if metodo == "crescimento":
        g = crescimento
        extremos = rodar("media", (1 + g) * (1 + variacao) - 1, (1 + g) * (1 - variacao) - 1)
        central = rodar("media", g, g)["Otimista"]
        return {"Pessimista": extremos["Pessimista"], "Central": central, "Otimista": extremos["Otimista"]}
    c = rodar(metodo, variacao, -variacao)
    return {"Pessimista": c["Pessimista"], "Central": c["Neutro"], "Otimista": c["Otimista"]}


def comparar_anos(base: BaseMensal, cliente: Cliente, metodo: str = "tendencia", crescimento: float | None = None,
                  variacao: float = 0.15) -> ComparativoAnual:
    rb = base.receita_bruta()
    com_receita = rb.index[rb > 0]
    if len(com_receita) == 0:
        raise ValueError("A base não tem receita: importe os relatórios antes de comparar os anos.")
    ultimo = com_receita.max()
    ano_atual = ultimo.year if ultimo.month < 12 else ultimo.year + 1
    proximo = ano_atual + 1 if ultimo.month < 12 else ano_atual
    if ultimo.month == 12:          # ano fechado: o "atual" passa a ser o seguinte, todo estimado
        ano_atual, proximo = ultimo.year + 1, ultimo.year + 2
    fim = pd.Period(year=proximo, month=12, freq="M")
    meses_proj = (fim.year - ultimo.year) * 12 + fim.month - ultimo.month
    hist = base.recorte(fim=ultimo)

    # comparação no mesmo período (meses reais do ano corrente × mesmos meses do ano anterior)
    meses_atual = [p for p in com_receita if p.year == ultimo.year]
    anteriores = [p - 12 for p in meses_atual]
    mesmo_ok = bool(meses_atual) and all(p in rb.index and rb[p] > 0 for p in anteriores)
    if crescimento is None and mesmo_ok:
        crescimento_obs = float(rb[meses_atual].sum() / rb[anteriores].sum() - 1)
    else:
        crescimento_obs = None
    if metodo == "crescimento" and crescimento is None:
        crescimento = crescimento_obs or 0.0

    alertas = Alertas()
    cen = _cenarios(hist, cliente, meses_proj, metodo, crescimento or 0.0, variacao, alertas)
    central = cen["Central"]
    res, rb_full = central.resultado, central.base_completa.receita_bruta()
    atual_reg = REGIME_DO_CADASTRO.get(cliente.regime_atual)

    # ---------------- uma linha por ano ----------------
    linhas = []
    for ano in range(com_receita.min().year, proximo + 1):
        meses = pd.period_range(f"{ano}-01", f"{ano}-12", freq="M")
        reais = [p for p in meses if p in com_receita]
        if ano < ultimo.year or (ano == ultimo.year and ultimo.month == 12):
            usados, situacao = pd.PeriodIndex(reais, freq="M"), "realizado" if len(reais) == 12 else "parcial"
        elif ano == proximo and ano != ultimo.year:
            usados, situacao = meses, "projetado"
        else:
            usados, situacao = meses, "realizado + estimado" if reais else "estimado"
        if len(usados) == 0:
            continue
        r = res.resumo(usados)
        sem_dre = bool(reais) and not _tem_dre(base, reais)
        linha = {"ano": ano, "situacao": situacao, "sem_dre": sem_dre, "meses_reais": len(reais), "meses_estimados": len(usados) - len(reais),
                 "receita": float(rb_full.reindex(usados).fillna(0).sum())}
        validos = r[r["elegivel"]]
        if ano < INICIO_HIBRIDO:      # a opção pelo IBS/CBS por fora só existe a partir de 2027
            validos = validos.drop(index="simples_hibrido", errors="ignore")
        if sem_dre:                   # sem custos/despesas o Lucro Real sairia sobre lucro ≈ receita: não comparar
            validos = validos.drop(index="real", errors="ignore")
            alertas.atencao("Comparação", f"{ano}: meses reais sem DRE (custos e despesas). O Lucro Real deste ano não "
                                          "é mostrado; importe a DRE para comparar.")
        for reg in REGIMES:
            ok = reg in validos.index
            linha[reg] = float(validos.at[reg, "tributos"]) if ok else np.nan
            linha[f"carga_{reg}"] = float(validos.at[reg, "carga"]) if ok else np.nan
        if not validos.empty:
            melhor = validos["tributos"].idxmin()
            linha["menor"] = melhor
            if atual_reg in validos.index:
                linha["economia_vs_atual"] = linha[atual_reg] - linha[melhor]
        linhas.append(linha)
    anos = pd.DataFrame(linhas).set_index("ano")
    completos = anos["meses_reais"] + anos["meses_estimados"] == 12
    anterior_completo = completos.shift(1, fill_value=False).astype(bool)
    anos["var_receita"] = np.where(completos & anterior_completo, anos["receita"] / anos["receita"].shift(1) - 1, np.nan)

    # ---------------- mesmo período ----------------
    mesmo = pd.DataFrame()
    periodo_txt = ""
    if mesmo_ok:
        ra, rp = res.resumo(pd.PeriodIndex(anteriores, freq="M")), res.resumo(pd.PeriodIndex(meses_atual, freq="M"))
        reg_linhas = [{"item": "Receita", "chave": "receita", "anterior": float(rb[anteriores].sum()),
                       "atual": float(rb[meses_atual].sum())}]
        sem_dre_mp = not (_tem_dre(base, anteriores) and _tem_dre(base, meses_atual))
        for reg in REGIMES:
            if reg == "simples_hibrido" and ultimo.year < INICIO_HIBRIDO:
                continue
            if reg == "real" and sem_dre_mp:
                continue
            if reg in ra.index and reg in rp.index and ra.at[reg, "elegivel"] and rp.at[reg, "elegivel"]:
                reg_linhas.append({"item": ROTULO[reg], "chave": reg, "anterior": float(ra.at[reg, "tributos"]),
                                   "atual": float(rp.at[reg, "tributos"])})
        mesmo = pd.DataFrame(reg_linhas)
        mesmo["variacao"] = mesmo["atual"] / mesmo["anterior"].replace(0, np.nan) - 1
        m0, m1 = min(meses_atual), max(meses_atual)
        periodo_txt = MESES[m0.month - 1] + ("" if m0 == m1 else f"–{MESES[m1.month - 1]}")

    # ---------------- receita mês a mês por ano ----------------
    ini = pd.Period(year=com_receita.min().year, month=1, freq="M")
    serie = rb_full.loc[ini:fim]
    mensal = pd.DataFrame({"competencia": serie.index, "receita": serie.values})
    mensal["ano"] = [p.year for p in mensal["competencia"]]
    mensal["mes"] = [p.month for p in mensal["competencia"]]
    mensal["tipo"] = ["real" if p in com_receita else ("projetado" if p.year == proximo else "estimado")
                      for p in mensal["competencia"]]
    mensal = mensal[(mensal["receita"] > 0) | (mensal["tipo"] != "real")]
    mensal = mensal[~((mensal["tipo"] == "real") & ~mensal["competencia"].isin(com_receita))]

    # ---------------- cenários do próximo ano ----------------
    meses_prox = pd.period_range(f"{proximo}-01", f"{proximo}-12", freq="M")
    cl = []
    for nome, c in cen.items():
        r = c.resultado.resumo(meses_prox)
        for reg in r.index:
            cl.append({"cenario": nome, "regime": reg, "rotulo": ROTULO[reg], "receita": float(r.at[reg, "receita"]),
                       "tributos": float(r.at[reg, "tributos"]) if r.at[reg, "elegivel"] else np.nan,
                       "carga": float(r.at[reg, "carga"]) if r.at[reg, "elegivel"] else np.nan,
                       "melhor": bool(r.at[reg, "melhor"])})
    cenarios = pd.DataFrame(cl)
    return ComparativoAnual(ano_atual=ultimo.year if ultimo.month < 12 else ano_atual, proximo_ano=proximo,
                            anos=anos, mesmo_periodo=mesmo, periodo_txt=periodo_txt, mensal=mensal, cenarios=cenarios,
                            crescimento_observado=crescimento_obs, metodo=metodo, alertas=alertas)
