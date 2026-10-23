"""
Projeção dos próximos meses em três cenários e recálculo dos regimes.

- Receita de cada anexo: tendência linear (mínimos quadrados) sobre a janela dos últimos meses
  com receita, ou a média (``Projecao.metodo``). Índice sazonal mensal só com 2 anos completos.
- Itens que acompanham a receita (proporção média da janela): custos, insumos, fretes,
  devoluções, ICMS e ISS.
- Itens fixos (média dos últimos 3 meses): folha, pró-labore, FGTS, despesas, energia, aluguel,
  serviços, uso e consumo, receitas financeiras e ajustes do LALUR. Imobilizado projetado em zero.
- Otimista/Pessimista: receita do Neutro × (1 ± variação). Folha e despesas fixas não mudam,
  por isso o Fator R e a margem reagem ao cenário.
- Cada cenário é anexado ao histórico e o cálculo roda na série inteira (RBT12, trimestres,
  prejuízo e saldo credor saem certos); depois recortam-se os meses projetados.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .alertas import Alertas
from .base import COLUNAS, RECEITAS, BaseMensal
from .calculo import Resultado, calcular
from .cliente import Cliente

VARIAVEIS = ["custos", "cred_insumos", "cred_fretes", "devolucoes", "icms_debito", "icms_credito", "iss"]
FIXOS = ["salarios", "pro_labore", "fgts", "cpp_das", "despesas", "cred_energia", "cred_aluguel", "cred_servicos",
         "uso_consumo", "receitas_financeiras", "adicoes", "exclusoes"]
CENARIOS = ("Neutro", "Otimista", "Pessimista")


@dataclass
class Cenario:
    nome: str
    variacao: float
    base_projetada: BaseMensal      # só os meses projetados
    base_completa: BaseMensal       # histórico + projeção
    resultado: Resultado            # calculado na série completa

    @property
    def meses(self) -> pd.PeriodIndex:
        return self.base_projetada.meses


def _indice_sazonal(rec: pd.Series, modo: str, al: Alertas) -> pd.Series:
    neutro = pd.Series(1.0, index=range(1, 13))
    if modo == "nao":
        return neutro
    anos = [a for a in sorted(set(rec.index.year)) if (rec.index.year == a).sum() == 12 and rec[rec.index.year == a].sum() > 0]
    if len(anos) < 2:
        if modo == "sim":
            al.atencao("Projeção", "Sazonalidade pedida, mas há menos de 2 anos completos; não aplicada.")
        return neutro
    razoes = [pd.Series(rec[rec.index.year == a].values / rec[rec.index.year == a].mean(), index=range(1, 13))
              for a in anos]
    indice = pd.concat(razoes, axis=1).mean(axis=1)
    if not np.isfinite(indice.to_numpy()).all() or (indice <= 0).any():
        al.atencao("Projeção", "Índice sazonal nulo ou inválido: sazonalidade não aplicada; "
                   "revise os meses sem receita no histórico.")
        return neutro
    al.info("Projeção", f"Índice sazonal aplicado ({len(anos)} anos completos).")
    return indice / indice.mean()


def _tendencia(y: np.ndarray, passos: int, metodo: str) -> np.ndarray:
    if metodo == "media" or len(y) < 3 or np.allclose(y, 0):
        return np.full(passos, y.mean() if len(y) else 0.0)
    t = np.arange(len(y))
    a, b = np.polyfit(t, y, 1)
    return b + a * np.arange(len(y), len(y) + passos)


def projetar(base: BaseMensal, cliente: Cliente, alertas: Alertas | None = None) -> dict[str, Cenario]:
    al = alertas or Alertas()
    cfg = cliente.projecao
    d = base.dados
    rb = base.receita_bruta()
    com_receita = rb.index[rb > 0]
    if len(com_receita) == 0:
        raise ValueError("A base não tem receita: importe os relatórios antes de projetar.")
    ultimo = com_receita.max()
    hist = base.recorte(fim=ultimo)
    janela = hist.dados.loc[hist.dados.index[-min(cfg.janela, len(hist.meses)):]]
    if len(janela) < 3:
        al.critico("Projeção", "Menos de 3 meses de histórico: projeção pela média, baixa confiabilidade.")
    meses = pd.period_range(ultimo + 1, periods=cfg.meses, freq="M", name="competencia")
    saz = _indice_sazonal(rb.loc[:ultimo], cfg.sazonalidade, al)
    s_jan = np.array([saz[m] for m in janela.index.month])
    s_fut = np.array([saz[m] for m in meses.month])

    receitas = {}
    for col in RECEITAS:
        y = janela[col].fillna(0).to_numpy()
        fut = _tendencia(y / s_jan, len(meses), cfg.metodo) * s_fut
        if (fut < 0).any():
            al.atencao("Projeção", f"Tendência de queda levaria '{COLUNAS[col][1]}' abaixo de zero; zerado.")
        if y.mean() > 0 and abs(fut[-1] - y.mean()) > 0.5 * y.mean():
            al.atencao("Projeção", f"Tendência forte em '{COLUNAS[col][1]}' (mais de 50% em relação à média). "
                                   "Avalie o método 'média' ou uma janela maior.")
        receitas[col] = np.clip(fut, 0, None)

    rec_jan = janela[RECEITAS].fillna(0).sum(axis=1).sum()
    razao = {c: (janela[c].fillna(0).sum() / rec_jan if rec_jan else 0.0) for c in VARIAVEIS}
    fixos = hist.dados[FIXOS].tail(3).mean()          # NaN fica NaN (não informado)

    cenarios = {}
    for nome, var in (("Neutro", 0.0), ("Otimista", cfg.otimista), ("Pessimista", cfg.pessimista)):
        p = pd.DataFrame(np.nan, index=meses, columns=list(COLUNAS))
        for col in RECEITAS:
            p[col] = receitas[col] * (1 + var)
        total = p[RECEITAS].sum(axis=1)
        for c in VARIAVEIS:
            p[c] = total * razao[c] if janela[c].notna().any() else np.nan
        for c in FIXOS:
            p[c] = fixos[c]
        p["imobilizado"] = 0.0
        proj = BaseMensal(p, pd.DataFrame(f"projeção {nome.lower()}", index=meses, columns=list(COLUNAS)))
        completa = hist.copia()
        completa.mesclar(p, f"projeção {nome.lower()}")
        cenarios[nome] = Cenario(nome, var, proj, completa, calcular(completa, cliente, Alertas()))
        al.estender(cenarios[nome].resultado.alertas)
    return cenarios
