"""
Painel da carteira: roda o planejamento de todos os clientes e lista quem deveria mudar de regime.

A opção pelo regime é irretratável no ano-calendário: o painel é para novembro/dezembro, antes do
prazo de janeiro. Para cada cliente com base, compara o custo projetado (cenário Neutro) do regime
atual com o de menor carga e anualiza a diferença (× 12 ÷ meses projetados).
"""
from __future__ import annotations

from typing import Callable

import pandas as pd

from .base import BaseMensal
from .calculo import ROTULO
from .cliente import Cliente, listar_clientes
from .planejamento import gerar_planejamento

REGIME_DO_CADASTRO = {"simples": "simples", "presumido": "presumido", "real": "real"}
MARGEM_MINIMA = 0.03        # abaixo de 3% de vantagem, a recomendação é "manter / avaliar"


def analisar_cliente(cliente: Cliente, base: BaseMensal | None = None) -> dict:
    base = base if base is not None else BaseMensal.carregar(cliente.pasta())
    linha = {"cliente": cliente.nome, "cnpj": cliente.cnpj, "id": cliente.id,
             "regime_atual": ROTULO.get(REGIME_DO_CADASTRO.get(cliente.regime_atual, ""), cliente.regime_atual)}
    if base.receita_bruta().sum() <= 0:
        return {**linha, "situacao": "SEM BASE", "leitura": "Importe os relatórios do Domínio."}
    try:
        pl = gerar_planejamento(cliente, base, com_transicao=False, com_equilibrio=False)
    except Exception as erro:  # noqa: BLE001 — um cliente com problema não derruba o painel
        return {**linha, "situacao": "ERRO", "leitura": str(erro)}
    neutro = pl.resumo[pl.resumo.cenario == "Neutro"].set_index("regime")
    m = pl.melhor("Neutro")
    fator = 12 / len(pl.meses_projetados)
    atual = REGIME_DO_CADASTRO.get(cliente.regime_atual)
    custo_atual = neutro.at[atual, "tributos"] if atual in neutro.index and neutro.at[atual, "elegivel"] else float("nan")
    economia = (custo_atual - m["tributos"]) * fator if m is not None else float("nan")
    criticos = pl.alertas.contagem()["CRÍTICO"]
    if m is None:
        situacao, leitura = "SEM RESULTADO", "Nenhum regime calculável com os dados atuais."
    elif m["regime"] in (atual, f"{atual}_hibrido"):
        situacao, leitura = "MANTER", f"O regime atual é o de menor carga ({m['rotulo']})."
    elif pd.isna(custo_atual):
        situacao, leitura = "MUDAR", f"Regime atual não aplicável aos dados; menor carga: {m['rotulo']}."
    elif custo_atual - m["tributos"] < MARGEM_MINIMA * custo_atual:
        situacao, leitura = "AVALIAR", f"{m['rotulo']} é menor, mas por menos de 3%."
    else:
        situacao, leitura = "MUDAR", f"Mudar para {m['rotulo']}."
    if criticos:
        leitura += f" Há {criticos} alerta(s) crítico(s): revisar a base antes de decidir."
    jan = pl.prazos[pl.prazos.evento.str.contains("Simples", na=False)]["data"]
    return {**linha, "situacao": situacao, "menor_carga": m["rotulo"] if m is not None else "",
            "custo_atual_ano": custo_atual * fator, "custo_menor_ano": m["tributos"] * fator if m is not None else None,
            "economia_ano": economia, "carga_menor": m["carga"] if m is not None else None,
            "alertas_criticos": criticos, "decidir_ate": jan.min() if len(jan) else None, "leitura": leitura}


def analisar_carteira(clientes: list[Cliente] | None = None,
                      progresso: Callable[[int, int, str], None] | None = None) -> pd.DataFrame:
    """Uma linha por cliente, ordenada por situação (MUDAR primeiro) e economia anual."""
    clientes = clientes if clientes is not None else listar_clientes()
    linhas = []
    for i, c in enumerate(clientes, start=1):
        if progresso:
            progresso(i, len(clientes), c.nome)
        linhas.append(analisar_cliente(c))
    df = pd.DataFrame(linhas)
    if df.empty:
        return df
    ordem = {"MUDAR": 0, "AVALIAR": 1, "MANTER": 2, "SEM RESULTADO": 3, "SEM BASE": 4, "ERRO": 5}
    df["_o"] = df["situacao"].map(ordem)
    if "economia_ano" not in df:
        df["economia_ano"] = float("nan")
    return df.sort_values(["_o", "economia_ano"], ascending=[True, False]).drop(columns="_o").reset_index(drop=True)
