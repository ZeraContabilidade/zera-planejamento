"""Testes do motor com memória de cálculo nos comentários."""
import math

import pandas as pd
import pytest

from zera_planejamento.base import BaseMensal
from zera_planejamento.calculo import calcular, simular_transicao
from zera_planejamento.calculo.comum import Contexto
from zera_planejamento.calculo.presumido import calcular_presumido, excesso_lc224
from zera_planejamento.calculo.real import calcular_real
from zera_planejamento.calculo.simples import calcular_simples
from zera_planejamento.cliente import Cliente
from zera_planejamento.regras.reforma import RegrasReforma, partilha_simples
from zera_planejamento.regras.simples import aliquota_efetiva, janela_rbt12


def base(inicio, fim, **colunas):
    idx = pd.period_range(inicio, fim, freq="M")
    return BaseMensal.de_dataframe(pd.DataFrame({k: float(v) for k, v in colunas.items()}, index=idx))


def perto(a, b, tol=0.01):
    assert math.isclose(a, b, abs_tol=tol), f"{a} != {b}"


CLIENTE = Cliente(nome="Teste", iss_aliquota=0.02, rat=0.0, terceiros=0.0)


# ---------------- Simples ----------------
def test_aliquota_efetiva():
    # (1.000.000 × 16% − 35.640) / 1.000.000 = 12,436%
    perto(aliquota_efetiva(1_000_000, "III")[0], 0.12436, 1e-9)
    perto(aliquota_efetiva(150_000, "I")[0], 0.04, 1e-9)


def test_janela_rbt12_muda_em_2027():
    assert janela_rbt12(pd.Period("2026-12", "M")) == (pd.Period("2025-12", "M"), pd.Period("2026-11", "M"))
    # LC 214/2025: a partir de jan/2027 o mês anterior sai da conta
    assert janela_rbt12(pd.Period("2027-05", "M")) == (pd.Period("2026-04", "M"), pd.Period("2027-03", "M"))


def test_das_e_fator_r():
    # 100 mil/mês, folha 30 mil -> Fator R 30% -> Anexo III; RBT12 1,2 mi
    # (1.200.000 × 16% − 35.640) / 1.200.000 = 13,03% -> DAS 13.030
    b = base("2025-01", "2026-03", rec_fator_r=100_000, salarios=25_000, pro_labore=5_000)
    s = calcular_simples(Contexto(b, CLIENTE)).iloc[-1]
    assert s["anexo_fator_r"] == "III"
    perto(s["das"], 13_030)
    # folha 20 mil (16,7%) -> Anexo V: (1.200.000 × 20,5% − 17.100)/1.200.000 = 19,075%
    b2 = base("2025-01", "2026-03", rec_fator_r=100_000, salarios=15_000, pro_labore=5_000)
    perto(calcular_simples(Contexto(b2, CLIENTE)).iloc[-1]["das"], 19_075)


def test_exclusao_por_receita_anual():
    b = base("2026-01", "2026-12", rec_anexo_iii=600_000)   # 7,2 mi no ano
    s = calcular_simples(Contexto(b, CLIENTE))
    # acumulado passa de 5,76 mi (4,8 mi + 20%) em out/26 -> excluída a partir de nov/26
    assert s.loc["2026-10", "elegivel"] and not s.loc["2026-11", "elegivel"]


def test_hibrido_usa_partilha():
    p = partilha_simples(2027, "III", 4)
    assert p is not None and math.isclose(sum(p.values()), 1.0, abs_tol=0.002)
    assert partilha_simples(2027, "II", 1) is None
    b = base("2026-01", "2027-03", rec_anexo_iii=100_000)
    s = calcular_simples(Contexto(b, CLIENTE)).loc["2027-03"]
    perto(s["das_cbs"], s["das"] * partilha_simples(2027, "III", s["faixa"])["cbs"])
    # CBS por fora: 100.000 × (9,21% − 0,1 p.p.) = 9.110 (sem créditos)
    perto(s["hibrido_cbs"], 9_110)


# ---------------- Presumido ----------------
def test_presumido_servico_trimestre():
    # 100 mil/mês de serviço em 2026: PIS+Cofins 3,65%; base 32% = 96 mil no tri
    # IRPJ = 15% × 96.000 + 10% × (96.000 − 60.000) = 18.000 ; CSLL = 9% × 96.000 = 8.640
    b = base("2026-07", "2026-09", rec_anexo_iii=100_000)
    p = calcular_presumido(Contexto(b, CLIENTE))
    perto(p["pis"].sum(), 1_950)
    perto(p["cofins"].sum(), 9_000)
    perto(p["irpj"].sum(), 18_000)
    perto(p["csll"].sum(), 8_640)
    perto(p["iss"].sum(), 6_000)       # 2% estimado (cliente no Simples)


def test_lc224_trimestral_com_ajuste_anual():
    ctx = Contexto(base("2026-01", "2026-12", rec_anexo_iii=1), CLIENTE)
    rec = pd.Series([1.5e6, 1.0e6, 1.3e6, 1.4e6], index=[20261, 20262, 20263, 20264])
    exc = excesso_lc224(rec, pd.Series(3, index=rec.index), pd.Period("2026-01", "M"), ctx)
    perto(exc[20261], 250_000)      # 1,5 − 1,25
    perto(exc[20262], 0)
    perto(exc[20263], 0)            # 1,25 + saldo 0,25 = 1,5 > 1,3
    perto(exc[20264], -50_000)      # ajuste: (5,2 − 5,0) − 0,25 já tributado
    perto(exc.sum(), 200_000)


def test_presumido_2027_troca_pis_cofins_por_cbs_ibs():
    # CBS 9,11% + IBS 0,1% sobre (100.000 − ISS 2.000) − créditos de 20.000
    b = base("2027-01", "2027-03", rec_anexo_iii=100_000, cred_insumos=20_000)
    p = calcular_presumido(Contexto(b, CLIENTE)).iloc[0]
    assert p["pis"] == 0 and p["cofins"] == 0
    perto(p["cbs"], (98_000 - 20_000) * 0.0911)
    perto(p["ibs"], (98_000 - 20_000) * 0.001)


# ---------------- Real ----------------
def test_real_trimestre_creditos():
    # comércio 200 mil, compras 100 mil (sem ICMS: cliente fora do Simples, ICMS informado zero)
    cli = Cliente(nome="R", regime_atual="presumido", rat=0, terceiros=0)
    b = base("2026-07", "2026-09", rec_anexo_i=200_000, cred_insumos=100_000, custos=120_000, despesas=40_000,
             adicoes=2_000, icms_debito=0, icms_credito=0, iss=0)
    cli.fap = 0
    r = calcular_real(Contexto(b, cli))
    # PIS/Cofins = (200.000 − 100.000) × 9,25% = 9.250/mês
    perto((r["pis"] + r["cofins"]).iloc[0], 9_250)
    # lucro/mês = 200.000 − 120.000 − 40.000 − 9.250 + 2.000 = 32.750 -> tri 98.250
    # IRPJ = 15% × 98.250 + 10% × 38.250 = 18.562,50 ; CSLL = 8.842,50
    perto(r["irpj"].sum(), 18_562.50)
    perto(r["csll"].sum(), 8_842.50)


def test_real_compensa_prejuizo_entre_trimestres():
    cli = Cliente(nome="R", regime_atual="presumido", rat=0, terceiros=0)
    # T1 prejuízo de 300 mil; T2 lucro de 300 mil -> compensa 30% (90 mil)
    idx = pd.period_range("2026-01", "2026-06", freq="M")
    df = pd.DataFrame({"rec_anexo_iii": [0, 0, 0, 100_000, 100_000, 100_000],
                       "despesas": [100_000, 100_000, 100_000, 0, 0, 0], "iss": 0.0, "icms_debito": 0.0,
                       "icms_credito": 0.0}, index=idx)
    r = calcular_real(Contexto(BaseMensal.de_dataframe(df), cli))
    lucro_t2 = r.loc["2026-04":"2026-06", "lucro_real"].sum()
    perto(r["prejuizo_compensado"].sum(), 0.30 * lucro_t2)
    base_t2 = lucro_t2 * 0.70
    perto(r.loc["2026-04":"2026-06", "irpj"].sum(), 0.15 * base_t2 + 0.10 * max(0, base_t2 - 60_000))


# ---------------- Reforma ----------------
def test_calendario_reforma():
    rr = RegrasReforma()
    assert rr.cbs(2026) == 0 and rr.pis_cofins_vigente(2026)
    perto(rr.cbs(2027), 0.0911, 1e-12)
    perto(rr.ibs(2030), 0.187 * 0.20, 1e-12)
    assert rr.fator_icms_iss(2029) == 0.9 and rr.fator_icms_iss(2033) == 0


def test_motor_e_transicao():
    b = base("2025-01", "2026-12", rec_anexo_iii=100_000, salarios=20_000, pro_labore=5_000, fgts=1_600,
             custos=20_000, despesas=30_000, cred_insumos=10_000)
    r = calcular(b, CLIENTE)
    res = r.resumo(pd.period_range("2026-01", "2026-12", freq="M"))
    assert res["melhor"].sum() == 1
    t = simular_transicao(b, CLIENTE)
    assert list(t.index) == list(range(2026, 2034))
    perto(t.loc[2027, "simples"], t.loc[2026, "simples"])     # DAS "por dentro" não muda
    assert t.loc[2033, "presumido"] > t.loc[2026, "presumido"]
    assert not pd.isna(t.loc[2027, "simples_hibrido"])
