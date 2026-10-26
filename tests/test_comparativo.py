"""Comparação entre anos: realizado, mesmo período, estimativa do ano corrente e projeção do próximo ano."""
import math

import numpy as np
import pandas as pd

from zera_planejamento.base import BaseMensal
from zera_planejamento.cliente import Cliente
from zera_planejamento.comparativo import comparar_anos

CLIENTE = Cliente(nome="Consultoria Exemplo", regime_atual="presumido", iss_aliquota=0.02, rat=0.0, terceiros=0.0)


def perto(a, b, tol=0.01):
    assert math.isclose(a, b, abs_tol=tol), f"{a:,.2f} != {b:,.2f}"


def base_dois_anos():
    # 2025: R$ 50 mil/mês de serviços (Anexo III); jan–set/2026: R$ 60 mil/mês. Folha 10 + 5 mil, despesas 20 mil.
    idx = pd.period_range("2025-01", "2026-09", freq="M")
    return BaseMensal.de_dataframe(pd.DataFrame({
        "rec_anexo_iii": [50_000.0] * 12 + [60_000.0] * 9, "salarios": 10_000.0, "pro_labore": 5_000.0,
        "custos": 0.0, "despesas": 20_000.0}, index=idx))


def test_anos_realizado_estimado_e_projetado_com_crescimento_informado():
    cp = comparar_anos(base_dois_anos(), CLIENTE, metodo="crescimento", crescimento=0.10)
    assert cp.ano_atual == 2026 and cp.proximo_ano == 2027
    a = cp.anos
    assert list(a.index) == [2025, 2026, 2027]
    assert list(a["situacao"]) == ["realizado", "realizado + estimado", "projetado"]
    assert list(a["meses_reais"]) == [12, 9, 0] and list(a["meses_estimados"]) == [0, 3, 12]
    # 2025 realizado: 12 × 50.000 = 600.000; Simples = 12 × 5.280 (10,56% sobre RBT12 de 600 mil) = 63.360
    perto(a.at[2025, "receita"], 600_000)
    perto(a.at[2025, "simples"], 63_360)
    # média dos últimos 12 meses (out/25–set/26) = (3 × 50.000 + 9 × 60.000) ÷ 12 = 57.500; × 1,10 = 63.250/mês
    # 2026 = 9 × 60.000 + 3 × 63.250 = 729.750;  2027 = 12 × 63.250 = 759.000
    perto(a.at[2026, "receita"], 729_750)
    perto(a.at[2027, "receita"], 759_000)
    perto(a.at[2026, "var_receita"], 729_750 / 600_000 - 1, 1e-9)
    # o Simples híbrido só existe a partir de 2027
    assert np.isnan(a.at[2025, "simples_hibrido"]) and np.isnan(a.at[2026, "simples_hibrido"])
    assert not np.isnan(a.at[2027, "simples_hibrido"])
    # menor carga e economia contra o regime atual (Presumido) saem do mesmo motor
    assert a.at[2027, "menor"] == "simples"
    perto(a.at[2027, "economia_vs_atual"], a.at[2027, "presumido"] - a.at[2027, "simples"])


def test_mesmo_periodo_e_crescimento_observado():
    # jan–set/2025 = 9 × 50.000 = 450.000; jan–set/2026 = 9 × 60.000 = 540.000 → +20%
    cp = comparar_anos(base_dois_anos(), CLIENTE, metodo="tendencia")
    assert cp.periodo_txt == "jan–set"
    perto(cp.crescimento_observado, 0.20, 1e-12)
    mp = cp.mesmo_periodo.set_index("chave")
    perto(mp.at["receita", "anterior"], 450_000)
    perto(mp.at["receita", "atual"], 540_000)
    # Simples jan–set/2025: 9 × 5.280 = 47.520 (RBT12 de 600 mil o ano todo)
    perto(mp.at["simples", "anterior"], 47_520)
    assert "simples_hibrido" not in mp.index
    # sem crescimento informado, o método "crescimento" usa o observado: 57.500 × 1,20 × 12 = 828.000 em 2027
    cp2 = comparar_anos(base_dois_anos(), CLIENTE, metodo="crescimento")
    perto(cp2.anos.at[2027, "receita"], 828_000)


def test_cenarios_do_proximo_ano():
    # cenários = central × (1 ± 15%) na receita: 759.000 × 1,15 = 872.850 e × 0,85 = 645.150
    cp = comparar_anos(base_dois_anos(), CLIENTE, metodo="crescimento", crescimento=0.10, variacao=0.15)
    rec = cp.cenarios.groupby("cenario")["receita"].first()
    perto(rec["Central"], 759_000)
    perto(rec["Otimista"], 872_850)
    perto(rec["Pessimista"], 645_150)
    trib = cp.cenarios.pivot(index="regime", columns="cenario", values="tributos")
    assert (trib["Pessimista"] <= trib["Central"]).all() and (trib["Central"] <= trib["Otimista"]).all()
    assert cp.cenarios.groupby("cenario")["melhor"].sum().eq(1).all()


def test_receita_mensal_por_ano_marca_real_estimado_e_projetado():
    cp = comparar_anos(base_dois_anos(), CLIENTE, metodo="media")
    m = cp.mensal
    assert set(m[m["ano"] == 2025]["tipo"]) == {"real"}
    t26 = m[m["ano"] == 2026].set_index("mes")["tipo"]
    assert t26[9] == "real" and t26[10] == "estimado" and t26[12] == "estimado"
    assert set(m[m["ano"] == 2027]["tipo"]) == {"projetado"} and len(m[m["ano"] == 2027]) == 12


def test_primeiro_ano_parcial_nao_tem_variacao():
    # histórico começando em jul/2025: 2025 é parcial e não serve de base para a variação de 2026
    idx = pd.period_range("2025-07", "2026-09", freq="M")
    b = BaseMensal.de_dataframe(pd.DataFrame({"rec_anexo_iii": 50_000.0}, index=idx))
    cp = comparar_anos(b, CLIENTE)
    assert cp.anos.at[2025, "situacao"] == "parcial" and cp.anos.at[2025, "meses_reais"] == 6
    assert np.isnan(cp.anos.at[2026, "var_receita"])
    assert cp.mesmo_periodo.empty and cp.crescimento_observado is None   # não há jan–set/2025 para comparar


def test_ano_sem_dre_nao_mostra_lucro_real():
    # 2025 só com receita (sem custos/despesas): o Real sairia sobre lucro ≈ receita → não é mostrado
    idx = pd.period_range("2025-01", "2026-09", freq="M")
    df = pd.DataFrame({"rec_anexo_iii": 50_000.0}, index=idx)
    df.loc["2026-01":, "custos"], df.loc["2026-01":, "despesas"] = 0.0, 20_000.0
    cp = comparar_anos(BaseMensal.de_dataframe(df), CLIENTE)
    assert np.isnan(cp.anos.at[2025, "real"]) and cp.anos.at[2025, "sem_dre"]
    assert not np.isnan(cp.anos.at[2026, "real"])
    assert "real" not in set(cp.mesmo_periodo["chave"])          # jan–set/2025 sem DRE: Real fora do mesmo período
    assert any("sem DRE" in a.mensagem for a in cp.alertas.itens)
