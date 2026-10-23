"""
Gráficos em PNG (Matplotlib) para o PDF.

Cores por regime validadas para daltonismo (ΔE ≥ 9 entre vizinhos); cada série também tem
marcador próprio e rótulo, para não depender só da cor.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

from ..calculo import ROTULO  # noqa: E402
from ..formatos import comp, pct  # noqa: E402

COR = {"simples": "#B07D1F", "simples_hibrido": "#1BAF7A", "presumido": "#2F6EA8", "real": "#A23E55"}
MARCA = {"simples": "o", "simples_hibrido": "D", "presumido": "s", "real": "^"}
PRETO, CINZA, TEXTO = "#111111", "#5F5F5F", "#1A1A1A"


def _estilo():
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": "#BBBBBB", "axes.labelcolor": TEXTO,
        "xtick.color": CINZA, "ytick.color": CINZA, "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "grid.color": "#E6E6E6", "grid.linewidth": 0.6, "axes.axisbelow": True,
        "legend.frameon": False, "savefig.dpi": 200,
    })


def mil(v, _=None) -> str:
    return f"R$ {v / 1000:,.0f} mil".replace(",", ".")


def _titulo(ax, titulo: str, sub: str):
    ax.set_title(titulo, loc="left", fontsize=12, fontweight="bold", color=PRETO, pad=22)
    ax.text(0, 1.02, sub, transform=ax.transAxes, fontsize=8.5, color=CINZA, va="bottom")


def _salvar(fig, caminho: Path) -> Path:
    fig.tight_layout()
    fig.savefig(caminho, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return caminho


def historico(mensal: pd.DataFrame, caminho: Path) -> Path:
    """Linhas: tributos de cada mês do histórico, por regime."""
    _estilo()
    fig, ax = plt.subplots(figsize=(10, 4.6))
    x = np.arange(len(mensal))
    finais = []
    for r in mensal.columns:
        y = mensal[r]
        if y.notna().sum() == 0:
            continue
        ax.plot(x, y, color=COR[r], marker=MARCA[r], markersize=4.5, linewidth=2, label=ROTULO[r])
        ult = y.last_valid_index()
        finais.append([y[ult], x[mensal.index.get_loc(ult)], r])
    amp = np.nanmax(mensal.to_numpy()) - np.nanmin(mensal.to_numpy()) if mensal.notna().any().any() else 1
    pos = []
    for v, _, _ in sorted(finais):
        pos.append(max(v, pos[-1] + amp * 0.06) if pos else v)
    for (v, xi, r), yp in zip(sorted(finais), pos):
        ax.annotate(mil(v), (xi, v), xytext=(xi + 0.6, yp), textcoords="data", fontsize=7.5, color=TEXTO, va="center",
                    arrowprops={"arrowstyle": "-", "color": COR[r], "lw": 0.6})
    passo = max(1, len(mensal) // 12)
    ax.set_xticks(x[::passo], [comp(m) for m in mensal.index[::passo]])
    ax.set_xlim(-0.5, len(mensal) - 0.5 + max(2, len(mensal) * 0.1))
    ax.yaxis.set_major_formatter(FuncFormatter(mil))
    _titulo(ax, "Tributos mês a mês no histórico, por regime",
            "Tributos sobre a receita, IRPJ/CSLL, ICMS, ISS e encargos patronais. FGTS fora (igual nos regimes).")
    ax.legend(loc="upper left", ncol=4, fontsize=8)
    return _salvar(fig, caminho)


def cenarios(resumo: pd.DataFrame, caminho: Path) -> Path:
    """Barras agrupadas: custo do semestre projetado por cenário e regime."""
    _estilo()
    nomes = list(dict.fromkeys(resumo["cenario"]))
    regimes = list(dict.fromkeys(resumo["regime"]))
    fig, ax = plt.subplots(figsize=(10, 4.8))
    larg = 0.8 / len(regimes)
    x = np.arange(len(nomes))
    topo = resumo.loc[resumo["elegivel"], "tributos"].max()
    for j, r in enumerate(regimes):
        for i, c in enumerate(nomes):
            lin = resumo[(resumo.cenario == c) & (resumo.regime == r)].iloc[0]
            pos = x[i] + (j - (len(regimes) - 1) / 2) * larg
            if not lin["elegivel"]:
                ax.bar(pos, topo * 0.04, larg * 0.9, color="white", edgecolor=COR[r], hatch="///", linewidth=1)
                ax.text(pos, topo * 0.06, "n/d", ha="center", fontsize=7, color=CINZA)
                continue
            ax.bar(pos, lin["tributos"], larg * 0.9, color=COR[r], edgecolor=PRETO if lin["melhor"] else "none",
                   linewidth=1.6 if lin["melhor"] else 0)
            ax.text(pos, lin["tributos"] + topo * 0.012, f"{mil(lin['tributos'])}\n{pct(lin['carga'], 1)}", ha="center",
                    va="bottom", fontsize=6.8, color=TEXTO, fontweight="bold" if lin["melhor"] else "normal")
    ax.set_xticks(x, [f"{c}\nreceita {mil(resumo[resumo.cenario == c]['receita'].iloc[0])}" for c in nomes])
    ax.yaxis.set_major_formatter(FuncFormatter(mil))
    ax.set_ylim(0, topo * 1.2)
    ax.grid(axis="x", visible=False)
    ax.legend(handles=[Patch(facecolor=COR[r], label=ROTULO[r]) for r in regimes], loc="upper left",
              ncol=len(regimes), fontsize=8)
    _titulo(ax, "Custo tributário do período projetado, por cenário",
            "Contorno preto e rótulo em negrito = menor carga do cenário. Abaixo do valor, a carga sobre a receita.")
    return _salvar(fig, caminho)


def sensibilidade(curva: pd.DataFrame, margem: float, equilibrio: pd.DataFrame, caminho: Path) -> Path | None:
    if curva is None or curva.empty:
        return None
    _estilo()
    fig, ax = plt.subplots(figsize=(10, 4.4))
    xs = curva["margem"] * 100
    for r in ("simples", "presumido", "real"):
        if r in curva:
            ax.plot(xs, curva[r], color=COR[r], linewidth=2, marker=MARCA[r], markevery=6, markersize=5, label=ROTULO[r])
    ax.axvline(margem * 100, color=CINZA, linestyle="--", linewidth=1)
    ax.text(margem * 100, ax.get_ylim()[1], f" margem projetada {pct(margem, 1)}", fontsize=7.5, color=CINZA, va="top")
    for outro, chave, desl in (("presumido", "Presumido", (-150, 22)), ("simples", "Simples", (14, -34))):
        lin = equilibrio[equilibrio.comparacao.str.contains(chave) & equilibrio.comparacao.str.startswith("Lucro Real")]
        if lin.empty or pd.isna(lin.equilibrio.iloc[0]):
            continue
        m = lin.equilibrio.iloc[0] * 100
        y = np.interp(m, xs, curva[outro])
        ax.plot([m], [y], marker="D", color=PRETO, markersize=6.5, zorder=5)
        ax.annotate(f"Real × {chave}: {pct(m / 100, 1)}", (m, y), xytext=desl, textcoords="offset points", fontsize=7.5,
                    bbox={"boxstyle": "round,pad=0.25", "fc": "white", "ec": "none"},
                    arrowprops={"arrowstyle": "-", "color": CINZA, "lw": 0.8})
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax.yaxis.set_major_formatter(FuncFormatter(mil))
    ax.set_xlabel("Margem operacional (receita − custos − despesas, antes de folha e tributos)")
    _titulo(ax, "Sensibilidade à margem — cenário Neutro",
            "Simples e Presumido não dependem do lucro; o Real acompanha a margem. Losangos = pontos de equilíbrio.")
    ax.legend(loc="upper left", ncol=3, fontsize=8)
    return _salvar(fig, caminho)


def transicao(tab: pd.DataFrame, caminho: Path) -> Path | None:
    if tab is None or tab.empty:
        return None
    _estilo()
    fig, ax = plt.subplots(figsize=(10, 4.2))
    for r in [c for c in COR if c in tab]:
        if tab[r].notna().any():
            ax.plot(tab.index, tab[r], color=COR[r], marker=MARCA[r], linewidth=2, markersize=5, label=ROTULO[r])
    ax.yaxis.set_major_formatter(FuncFormatter(mil))
    ax.set_xticks(list(tab.index))
    _titulo(ax, "Transição da Reforma (2026–2033) com os últimos 12 meses",
            "Mesma receita e custos; muda só a regra de cada ano (CBS/IBS, redução de ICMS/ISS, partilha do Simples).")
    ax.legend(loc="upper left", ncol=4, fontsize=8)
    return _salvar(fig, caminho)


def gerar(pl, pasta: Path) -> dict[str, Path]:
    pasta.mkdir(parents=True, exist_ok=True)
    mensal = pl.historico.mensal().loc[pl.meses_historico]
    saida = {"historico": historico(mensal, pasta / "grafico1_historico.png"),
             "cenarios": cenarios(pl.resumo, pasta / "grafico2_cenarios.png")}
    s = sensibilidade(pl.curva, pl.margem_projetada, pl.equilibrio, pasta / "grafico3_margem.png")
    t = transicao(pl.transicao, pasta / "grafico4_transicao.png")
    if s:
        saida["margem"] = s
    if t:
        saida["transicao"] = t
    return saida
