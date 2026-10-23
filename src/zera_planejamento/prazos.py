"""
Calendário de decisões tributárias do cliente (próximas datas a partir de hoje).

| Evento | Prazo | Base |
|---|---|---|
| Opção pelo Simples | último dia útil de janeiro | LC 123/2006, art. 16, § 2º; Res. CGSN 140/2018, art. 6º |
| Exclusão do Simples por opção | último dia útil de janeiro (efeito em 1º/jan) | LC 123/2006, art. 30, I, e § 1º, I |
| Lucro Presumido | 1ª quota ou quota única do IRPJ do 1º trimestre (último dia útil de abril) | Lei 9.430/1996, art. 5º e art. 26, § 1º |
| Lucro Real anual (estimativa) | pagamento da estimativa de janeiro (último dia útil de fevereiro) | Lei 9.430/1996, art. 3º |
| Simples híbrido (IBS/CBS por fora) | abril (efeito em julho) e setembro (efeito em janeiro) [CONFERIR] | LC 214/2025, art. 41; Res. CGSN |
| Alíquota de referência da CBS de 2027 | até 15/12/2026 [CONFERIR] | LC 214/2025 |

Dias úteis: segunda a sexta, sem feriados nacionais (fixos e Sexta-feira Santa).
"""
from __future__ import annotations

import datetime as dt

import pandas as pd

from .cliente import Cliente

FERIADOS_FIXOS = [(1, 1), (4, 21), (5, 1), (9, 7), (10, 12), (11, 2), (11, 15), (11, 20), (12, 25)]


def pascoa(ano: int) -> dt.date:
    """Domingo de Páscoa (algoritmo de Meeus/Jones/Butcher)."""
    a, b, c = ano % 19, ano // 100, ano % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mes = (h + l - 7 * m + 114) // 31
    dia = (h + l - 7 * m + 114) % 31 + 1
    return dt.date(ano, mes, dia)


def feriados(ano: int) -> set[dt.date]:
    return {dt.date(ano, m, d) for m, d in FERIADOS_FIXOS} | {pascoa(ano) - dt.timedelta(days=2)}


def dia_util(d: dt.date) -> bool:
    return d.weekday() < 5 and d not in feriados(d.year)


def ultimo_dia_util(ano: int, mes: int) -> dt.date:
    d = (dt.date(ano + mes // 12, mes % 12 + 1, 1)) - dt.timedelta(days=1)
    while not dia_util(d):
        d -= dt.timedelta(days=1)
    return d


def _proximo(hoje: dt.date, mes: int) -> dt.date:
    d = ultimo_dia_util(hoje.year, mes)
    return d if d >= hoje else ultimo_dia_util(hoje.year + 1, mes)


def prazos(cliente: Cliente, recomendado: str | None = None, hoje: dt.date | None = None) -> pd.DataFrame:
    """Próximos prazos de decisão, com destaque para os que dependem do regime recomendado."""
    hoje = hoje or dt.date.today()
    atual = cliente.regime_atual
    rec = {"simples_hibrido": "simples"}.get(recomendado, recomendado)
    linhas = []

    def add(data, evento, base, acao):
        linhas.append({"data": data, "dias": (data - hoje).days, "evento": evento, "base_legal": base,
                       "acao": acao})

    jan = _proximo(hoje, 1)
    if atual == "simples" and rec in ("presumido", "real"):
        add(jan, "Exclusão do Simples por opção (efeito em 1º de janeiro)", "LC 123/2006, art. 30, I, e § 1º, I",
            "DECIDIR")
    elif atual != "simples" and rec == "simples":
        add(jan, "Opção pelo Simples Nacional", "LC 123/2006, art. 16, § 2º; Res. CGSN 140/2018, art. 6º", "DECIDIR")
    else:
        add(jan, "Opção / exclusão do Simples (confirmar a manutenção do regime)", "LC 123/2006, art. 16, § 2º",
            "CONFERIR")
    add(_proximo(hoje, 2), "Lucro Real anual: a estimativa de janeiro formaliza a opção", "Lei 9.430/1996, art. 3º",
        "DECIDIR" if rec == "real" and atual != "real" else "INFORMATIVO")
    add(_proximo(hoje, 4), "Lucro Presumido: a 1ª quota do IRPJ do 1º trimestre formaliza a opção",
        "Lei 9.430/1996, art. 5º e art. 26, § 1º", "DECIDIR" if rec == "presumido" and atual != "presumido"
        else "INFORMATIVO")
    if atual == "simples" or rec == "simples":
        prox_abr, prox_set = _proximo(hoje, 4), _proximo(hoje, 9)
        add(min(prox_abr, prox_set), "Simples: opção semestral pelo IBS/CBS por fora (abril → julho; setembro → "
            "janeiro) [CONFERIR resolução do CGSN]", "LC 214/2025, art. 41", "AVALIAR" if recomendado ==
            "simples_hibrido" else "INFORMATIVO")
    ref_cbs = dt.date(2026, 12, 15)
    if hoje <= ref_cbs:
        add(ref_cbs, "Senado fixa a alíquota de referência da CBS de 2027: recalcular o planejamento [CONFERIR]",
            "LC 214/2025", "RECALCULAR")
    return pd.DataFrame(linhas).sort_values("data").reset_index(drop=True)
