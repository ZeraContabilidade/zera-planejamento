"""Reforma Tributária ano a ano (2026–2033), sensibilidade, regime diferenciado e diagnóstico de precisão."""
import math

import pandas as pd

from zera_planejamento.base import BaseMensal
from zera_planejamento.calculo import simular_transicao
from zera_planejamento.cliente import Cliente, Socio
from zera_planejamento.precisao import diagnosticar, nota
from zera_planejamento.transicao import indicadores, simular_reforma

CLI = Cliente(nome="Consultoria Exemplo", regime_atual="presumido", iss_aliquota=0.02, rat=0.0, terceiros=0.0)


def perto(a, b, tol=0.01):
    assert math.isclose(a, b, abs_tol=tol), f"{a:,.2f} != {b:,.2f}"


def base_servicos():
    # 2025 e 2026: R$ 50 mil/mês de serviços, sem folha, sem compras
    idx = pd.period_range("2025-01", "2026-12", freq="M")
    return BaseMensal.de_dataframe(pd.DataFrame({"rec_anexo_iii": 50_000.0, "custos": 0.0, "despesas": 0.0}, index=idx))


def test_presumido_2026_e_2033_calculados_a_mao():
    rf = simular_reforma(base_servicos(), CLI)
    # 2026 (receita 600.000): PIS 0,65% = 3.900; Cofins 3% = 18.000; ISS 2% = 12.000;
    #   IRPJ 15% × 32% × 600.000 = 28.800 (adicional zero: 48.000 por trimestre < 60.000); CSLL 9% × 192.000 = 17.280
    #   total = 79.980
    perto(rf.anual.at[2026, "presumido"], 79_980)
    # 2033: PIS/Cofins e ISS extintos; CBS 9,21% × 600.000 = 55.260; IBS 18,7% × 600.000 = 112.200
    #   total = 55.260 + 112.200 + 28.800 + 17.280 = 213.540
    perto(rf.anual.at[2033, "presumido"], 213_540)
    comp = rf.composicao.set_index(["ano", "regime", "tributo"])["valor"]
    perto(comp[(2033, "presumido", "CBS")], 55_260)
    perto(comp[(2033, "presumido", "IBS")], 112_200)
    assert (2033, "presumido", "ISS") not in comp.index and (2026, "presumido", "CBS") not in comp.index
    # a composição soma o total de cada ano e regime
    soma = rf.composicao.groupby(["ano", "regime"])["valor"].sum()
    for (ano, reg), total in soma.items():
        perto(total, rf.anual.at[ano, reg])


def test_totais_batem_com_a_transicao_do_motor():
    rf = simular_reforma(base_servicos(), CLI)
    ref = simular_transicao(base_servicos(), CLI)
    for ano in rf.anual.index:
        for reg in rf.carga.columns:
            if pd.notna(ref.at[ano, reg]) and pd.notna(rf.anual.at[ano, reg]):
                perto(rf.anual.at[ano, reg], ref.at[ano, reg])


def test_sensibilidade_da_cbs_e_regime_diferenciado():
    padrao = simular_reforma(base_servicos(), CLI)
    # CBS de referência 10% em vez de 9,21%: +0,79 p.p. × 600.000 = +4.740 em 2033
    alta = simular_reforma(base_servicos(), CLI, cbs=0.10)
    perto(alta.anual.at[2033, "presumido"] - padrao.anual.at[2033, "presumido"], 4_740)
    # redução de 60% (sem compras, não há crédito): CBS 55.260 × 40% = 22.104; IBS 112.200 × 40% = 44.880
    red = simular_reforma(base_servicos(), CLI, reducao=0.60)
    comp = red.composicao.set_index(["ano", "regime", "tributo"])["valor"]
    perto(comp[(2033, "presumido", "CBS")], 22_104)
    perto(comp[(2033, "presumido", "IBS")], 44_880)
    assert any("Redução" in o for o in red.observacoes)


def test_indicadores_da_reforma():
    rf = simular_reforma(base_servicos(), CLI)
    ind = indicadores(rf)
    assert ind["melhor_2026"] == rf.melhor[2026] and ind["melhor_2033"] == rf.melhor[2033]
    # Presumido: 79.980 → 213.540 = +167%
    perto(ind["variacao_atual"], 213_540 / 79_980 - 1, 1e-9)
    assert ind["ganho_acumulado"] >= 0
    assert list(rf.cronograma.index) == list(range(2026, 2034))
    assert rf.cronograma.at[2033, "icms_iss"] == 0 and rf.cronograma.at[2026, "pis_cofins"]


def test_diagnostico_de_precisao():
    # 6 meses só com receita: faltam histórico, DRE, folha, compras, sócios...
    idx = pd.period_range("2026-04", "2026-09", freq="M")
    pobre = BaseMensal.de_dataframe(pd.DataFrame({"rec_anexo_iii": 50_000.0}, index=idx))
    v = {x.titulo: x for x in diagnosticar(Cliente(nome="X"), pobre)}
    assert not v["13 meses ou mais de receita"].ok and not v["DRE em todos os últimos 12 meses"].ok
    assert nota(list(v.values()))[1] == "Baixa"
    # 24 meses completos, DRE, folha, compras, alíquotas e encargos conferidos, sócios e dados da Receita
    idx = pd.period_range("2024-10", "2026-09", freq="M")
    rica = BaseMensal.de_dataframe(pd.DataFrame({"rec_anexo_iii": 50_000.0, "custos": 5_000.0, "despesas": 8_000.0,
                                                 "salarios": 10_000.0, "pro_labore": 5_000.0,
                                                 "cred_servicos": 2_000.0}, index=idx))
    cli = Cliente(nome="Y", iss_aliquota=0.02, rat=0.01, fap=0.8, socios=[Socio("Ana")],
                  dados_receita={"cnpj": "11.222.333/0001-81"})
    n, nivel = nota(diagnosticar(cli, rica))
    assert n == 100 and nivel == "Alta"
