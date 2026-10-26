"""
Validação do planejamento com empresas fictícias calculadas à mão (números redondos, memória completa).

Cada caso monta uma base simples, roda o motor inteiro (``calcular``/``gerar_planejamento``) e confere o total
de cada regime com a conta feita pela lei. Se um destes testes falhar, ou a regra mudou (atualize a memória
com a base legal) ou o motor tem erro.
"""
import math

import pandas as pd

from zera_planejamento.base import BaseMensal
from zera_planejamento.calculo import calcular
from zera_planejamento.cliente import Cliente
from zera_planejamento.planejamento import gerar_planejamento

T1_2026 = pd.period_range("2026-01", "2026-03", freq="M")


def base(inicio, fim, **colunas):
    idx = pd.period_range(inicio, fim, freq="M")
    return BaseMensal.de_dataframe(pd.DataFrame({k: float(v) for k, v in colunas.items()}, index=idx))


def perto(a, b, tol=0.01):
    assert math.isclose(a, b, abs_tol=tol), f"{a:,.2f} != {b:,.2f}"


# Encargos simplificados (RAT e Terceiros zerados) para a conta caber na memória.
SERVICOS = Cliente(nome="Consultoria Exemplo", regime_atual="presumido", anexo_servico="III", iss_aliquota=0.02,
                   rat=0.0, terceiros=0.0)


def caso_servicos():
    # 2025 e 2026 iguais: R$ 50 mil/mês de serviços (Anexo III), salários R$ 10 mil, pró-labore R$ 5 mil,
    # despesas R$ 20 mil, sem custos, sem compras com crédito, sem receitas financeiras.
    return base("2025-01", "2026-03", rec_anexo_iii=50_000, salarios=10_000, pro_labore=5_000, fgts=0,
                custos=0, despesas=20_000)


def test_servicos_simples_anexo_iii():
    # RBT12 = 12 × 50.000 = 600.000 → 3ª faixa do Anexo III (13,5%, dedução 17.640)
    # alíquota efetiva = (600.000 × 13,5% − 17.640) ÷ 600.000 = 63.360 ÷ 600.000 = 10,56%
    # DAS do mês = 50.000 × 10,56% = 5.280 → 1º trimestre = 15.840 (ISS dentro do DAS)
    r = calcular(caso_servicos(), SERVICOS).resumo(T1_2026)
    perto(r.at["simples", "tributos"], 15_840.00)


def test_servicos_lucro_presumido():
    # 1º tri/2026: receita 150.000; presunção 32% → base 48.000 (abaixo de R$ 1,25 mi: sem acréscimo da LC 224)
    # IRPJ 15% × 48.000 = 7.200 (adicional: base < 20.000 × 3 = 60.000 → zero)
    # CSLL 9% × 48.000 = 4.320
    # PIS 0,65% × 150.000 = 975; Cofins 3% × 150.000 = 4.500 (cumulativos)
    # ISS 2% × 150.000 = 3.000
    # INSS patronal 20% × (10.000 + 5.000) × 3 = 9.000
    # total = 7.200 + 4.320 + 975 + 4.500 + 3.000 + 9.000 = 28.995
    r = calcular(caso_servicos(), SERVICOS).resumo(T1_2026)
    perto(r.at["presumido", "tributos"], 28_995.00)
    perto(r.at["presumido", "comp_irpj"], 7_200.00)
    perto(r.at["presumido", "comp_csll"], 4_320.00)


def test_servicos_lucro_real():
    # 1º tri/2026: PIS/Cofins não cumulativos 9,25% × 150.000 = 13.875 (sem créditos)
    # ISS 3.000; INSS patronal 9.000
    # lucro = 150.000 − despesas 60.000 − salários 30.000 − pró-labore 15.000 − INSS 9.000 − PIS/Cofins 13.875
    #         − ISS 3.000 = 19.125
    # IRPJ 15% × 19.125 = 2.868,75 (sem adicional); CSLL 9% × 19.125 = 1.721,25
    # total = 13.875 + 3.000 + 9.000 + 2.868,75 + 1.721,25 = 30.465
    r = calcular(caso_servicos(), SERVICOS).resumo(T1_2026)
    perto(r.at["real", "tributos"], 30_465.00)
    perto(r.at["real", "comp_irpj"], 2_868.75)


def test_servicos_ranking_e_economia():
    # Simples 15.840 < Presumido 28.995 < Real 30.465 → menor carga no Simples; economia sobre o 2º = 13.155
    r = calcular(caso_servicos(), SERVICOS).resumo(T1_2026)
    assert r.index[r["melhor"]].tolist() == ["simples"]
    perto(r.at["simples", "economia_vs_2o"], 28_995.00 - 15_840.00)
    perto(r.at["simples", "carga"], 15_840 / 150_000, 1e-9)


def test_comercio_simples_anexo_i():
    # R$ 100 mil/mês de mercadorias: RBT12 1.200.000 → 4ª faixa do Anexo I (10,7%, dedução 22.500)
    # alíquota = (1.200.000 × 10,7% − 22.500) ÷ 1.200.000 = 105.900 ÷ 1.200.000 = 8,825% → DAS 8.825/mês
    c = Cliente(nome="Loja Exemplo", regime_atual="simples", rat=0.0, terceiros=0.0)
    b = base("2025-01", "2026-03", rec_anexo_i=100_000)
    s = calcular(b, c).regimes["simples"]
    perto(s.loc["2026-03", "das"], 8_825.00)


def test_presumido_2027_com_cbs_ibs():
    # Jan/2027, serviços R$ 50 mil, ISS 2%: PIS/Cofins extintos; CBS = referência 9,21% − 0,1 p.p. = 9,11%;
    # IBS = 0,1%. Base sem ISS (LC 214, art. 12, § 2º): 50.000 − 1.000 = 49.000
    # CBS = 49.000 × 9,11% = 4.463,90; IBS = 49.000 × 0,1% = 49,00
    b = base("2026-01", "2027-01", rec_anexo_iii=50_000)
    p = calcular(b, SERVICOS).regimes["presumido"].loc["2027-01"]
    assert p["pis"] == 0 and p["cofins"] == 0
    perto(p["cbs"], 4_463.90)
    perto(p["ibs"], 49.00)


def test_cenarios_coerentes():
    # Otimista tem 15% mais receita que o Neutro e o Pessimista 15% menos; com folha e despesas fixas,
    # os tributos de cada regime seguem a mesma ordem (Pessimista ≤ Neutro ≤ Otimista)
    pl = gerar_planejamento(SERVICOS, caso_servicos(), com_transicao=False, com_equilibrio=False)
    r = pl.resumo.pivot(index="regime", columns="cenario", values="tributos")
    for reg in ("simples", "presumido"):
        assert r.at[reg, "Pessimista"] <= r.at[reg, "Neutro"] <= r.at[reg, "Otimista"]
    rec = pl.resumo.groupby("cenario")["receita"].first()
    perto(rec["Otimista"], rec["Neutro"] * 1.15, 0.05)
    perto(rec["Pessimista"], rec["Neutro"] * 0.85, 0.05)
    # receita constante: a projeção repete R$ 50 mil/mês
    perto(pl.cenarios["Neutro"].base_projetada.receita_bruta().mean(), 50_000.00)


def test_presumido_lc224_e_adicional_do_irpj():
    # R$ 700 mil/mês de serviços → 2.100.000 no trimestre; limite trimestral da LC 224/2025 = 1.250.000
    # excesso = 850.000; acréscimo de 10% na presunção de 32% → +3,2% × 850.000 = 27.200 na base
    # 1º tri: base IRPJ = 2.100.000 × 32% + 27.200 = 699.200
    #   IRPJ = 15% × 699.200 + 10% × (699.200 − 60.000) = 104.880 + 63.920 = 168.800
    #   CSLL ainda sem acréscimo (noventena até 03/2026): 9% × 672.000 = 60.480
    # 2º tri: CSLL já com acréscimo: 9% × 699.200 = 62.928
    b = base("2026-01", "2026-06", rec_anexo_iii=700_000)
    p = calcular(b, SERVICOS).regimes["presumido"]
    perto(p.loc["2026-01":"2026-03", "irpj"].sum(), 168_800.00)
    perto(p.loc["2026-01":"2026-03", "csll"].sum(), 60_480.00)
    perto(p.loc["2026-04":"2026-06", "csll"].sum(), 62_928.00)


def test_real_prejuizo_compensado_com_trava_de_30():
    # R$ 100 mil/mês de serviços, ISS 2%, sem folha; despesas de 150 mil/mês no 1º tri e 40 mil/mês no 2º
    # 1º tri: PIS/Cofins 9,25% × 300.000 = 27.750; ISS 6.000
    #   lucro = 300.000 − 450.000 − 27.750 − 6.000 = −183.750 → prejuízo a compensar, IRPJ/CSLL zero
    # 2º tri: lucro = 300.000 − 120.000 − 27.750 − 6.000 = 146.250
    #   compensação limitada a 30% = 43.875 → base 102.375
    #   IRPJ = 15% × 102.375 + 10% × (102.375 − 60.000) = 15.356,25 + 4.237,50 = 19.593,75
    #   CSLL = 9% × 102.375 = 9.213,75; saldo de prejuízo = 183.750 − 43.875 = 139.875
    idx = pd.period_range("2026-01", "2026-06", freq="M")
    df = pd.DataFrame({"rec_anexo_iii": 100_000.0, "custos": 0.0,
                       "despesas": [150_000.0] * 3 + [40_000.0] * 3}, index=idx)
    r = calcular(BaseMensal.de_dataframe(df), SERVICOS).regimes["real"]
    assert r.loc["2026-01":"2026-03", ["irpj", "csll"]].sum().sum() == 0
    perto(r.loc["2026-04":"2026-06", "irpj"].sum(), 19_593.75)
    perto(r.loc["2026-04":"2026-06", "csll"].sum(), 9_213.75)
    perto(r.loc["2026-06", "saldo_prejuizo"], 139_875.00)


def test_regime_diferenciado_reduz_so_o_debito_de_cbs_ibs():
    # Jan/2027, serviços R$ 50 mil, ISS 2%, compras com crédito R$ 10 mil; redução de 30% (LC 214/2025)
    # débito CBS = 49.000 × 9,11% × 70% = 3.124,73; crédito = 10.000 × 9,11% (alíquota cheia) = 911,00 → 2.213,73
    # débito IBS = 49.000 × 0,1% × 70% = 34,30; crédito = 10.000 × 0,1% = 10,00 → 24,30
    import dataclasses
    cli = dataclasses.replace(SERVICOS, reforma={"reducao_aliquota": 0.30})
    b = base("2026-01", "2027-01", rec_anexo_iii=50_000, cred_insumos=10_000)
    p = calcular(b, cli).regimes["presumido"].loc["2027-01"]
    perto(p["cbs"], 2_213.73)
    perto(p["ibs"], 24.30)
