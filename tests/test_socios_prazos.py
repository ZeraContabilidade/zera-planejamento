"""Pessoa física (Lei 15.270/2025), sublimite exato, sócio + empresa, pró-labore ótimo, prazos e carteira."""
import datetime as dt
import math

import pandas as pd

from zera_planejamento.base import BaseMensal
from zera_planejamento.calculo import calcular
from zera_planejamento.calculo.comum import Contexto
from zera_planejamento.calculo.simples import calcular_simples
from zera_planejamento.carteira import analisar_carteira
from zera_planejamento.cliente import Cliente, Socio
from zera_planejamento.prazos import pascoa, prazos, ultimo_dia_util
from zera_planejamento.regras.pessoa_fisica import (aliquota_irpfm, inss_pro_labore, irpfm, irrf_dividendos,
                                                    irrf_mensal)
from zera_planejamento.socios import otimizar_pro_labore, visao_socios


def base(inicio, fim, **colunas):
    idx = pd.period_range(inicio, fim, freq="M")
    return BaseMensal.de_dataframe(pd.DataFrame({k: v if isinstance(v, list) else float(v) for k, v in colunas.items()},
                                                index=idx))


def perto(a, b, tol=0.01):
    assert math.isclose(a, b, abs_tol=tol), f"{a} != {b}"


# ---------------- pessoa física ----------------
def test_inss_e_irrf_pro_labore():
    # INSS 11% limitado ao teto: 11% × 8.475,55 = 932,31
    perto(inss_pro_labore(10_000), 932.31)
    # R$ 5.000: base 5.000 − 607,20 (simplificado > INSS 550) = 4.392,80 → 22,5% − 675,49 = 312,89; redução 312,89 → 0
    perto(irrf_mensal(5_000, 550), 0.0)
    # R$ 7.000: base 7.000 − 770 = 6.230 → 27,5% − 908,73 = 804,52; redução 978,62 − 0,133145 × 7.000 = 46,60 → 757,92
    perto(irrf_mensal(7_000, 770), 757.92)
    # R$ 10.000: base 10.000 − 932,31 = 9.067,69 → 27,5% − 908,73 = 1.584,88; sem redução acima de R$ 7.350
    perto(irrf_mensal(10_000, 932.31), 1_584.88)
    # dependente: 2 × 189,59 + 770 = 1.149,18 de dedução → base 5.850,82 → 27,5% − 908,73 = 700,25; − 46,60 = 653,65
    perto(irrf_mensal(7_000, 770, dependentes=2), 653.65)


def test_dividendos_e_irpfm():
    assert irrf_dividendos(50_000) == 0.0                 # até R$ 50 mil no mês: sem retenção
    perto(irrf_dividendos(60_000), 6_000)                 # acima: 10% sobre o total
    assert aliquota_irpfm(600_000) == 0.0
    perto(aliquota_irpfm(900_000), 0.05, 1e-12)            # 900.000 ÷ 60.000 − 10 = 5%
    assert aliquota_irpfm(2_000_000) == 0.10
    # renda 1,5 mi (1,2 mi de lucros), IR da tabela 60 mil, PJ com 30%: 30% + 10% − 34% = 6% → redutor 72 mil
    # bruto 150.000 − 60.000 − 72.000 = 18.000
    r = irpfm(1_500_000, 1_200_000, 60_000, 0.30)
    perto(r["redutor"], 72_000)
    perto(r["devido"], 18_000)
    # PJ abaixo de 24%: sem redutor
    perto(irpfm(1_500_000, 1_200_000, 60_000, 0.20)["devido"], 90_000)


# ---------------- sublimite exato ----------------
CLI_SIMPLES = Cliente(nome="Comércio", regime_atual="simples", icms_aliquota_saida=0.18, rat=0.0, terceiros=0.0)


def test_sublimite_pelo_ano_anterior_tira_icms_do_das():
    # 2025: 320 mil/mês = 3,84 mi > 3,6 mi → impedida de recolher ICMS no DAS durante 2026 (LC 123, art. 20, § 1º)
    b = base("2025-01", "2026-12", rec_anexo_i=[320_000.0] * 12 + [250_000.0] * 12)
    s = calcular_simples(Contexto(b, CLI_SIMPLES)).loc["2026-07"]
    # RBT12 jul/26 = 6 × 320 mil + 6 × 250 mil = 3,42 mi → 5ª faixa do Anexo I:
    # (3.420.000 × 14,3% − 87.300) ÷ 3.420.000 = 11,7474%; DAS cheio 250.000 × 11,7474% = 29.368,42
    # sem os 33,5% de ICMS: 29.368,42 × 66,5% = 19.530,00; ICMS fora = 250.000 × 18% = 45.000
    assert s["faixa"] == 5
    perto(s["das"], 19_530.00)
    perto(s["das_icms_iss_excluido"], 9_838.42)
    perto(s["icms_fora_das"], 45_000)


def test_sem_sublimite_icms_fica_no_das():
    # 2025: 290 mil/mês = 3,48 mi (abaixo de 3,6 mi) e 2026 a 250 mil → ICMS continua no DAS
    b = base("2025-01", "2026-12", rec_anexo_i=[290_000.0] * 12 + [250_000.0] * 12)
    s = calcular_simples(Contexto(b, CLI_SIMPLES)).loc["2026-07"]
    assert s["icms_fora_das"] == 0 and s["das_icms_iss_excluido"] == 0


def test_sublimite_excesso_acima_de_20_no_ano():
    # 2026 a 400 mil/mês: acumulado passa de 4,32 mi (3,6 mi + 20%) em nov (4,4 mi) → impedida desde dez/26
    b = base("2025-01", "2026-12", rec_anexo_i=[100_000.0] * 12 + [400_000.0] * 12)
    s = calcular_simples(Contexto(b, CLI_SIMPLES))
    assert s.loc["2026-11", "das_icms_iss_excluido"] == 0
    assert s.loc["2026-12", "icms_fora_das"] > 0


# ---------------- sócio + empresa ----------------
def test_visao_socios_com_lucro_alto():
    c = Cliente(nome="Serviços", iss_aliquota=0.02, rat=0.0, terceiros=0.0, socios=[Socio("Ana", 1.0, 10_000)])
    b = base("2025-01", "2026-12", rec_anexo_iii=400_000, salarios=40_000, pro_labore=10_000, fgts=3_200,
             custos=50_000, despesas=60_000)
    meses = pd.period_range("2026-01", "2026-12", freq="M")
    v = visao_socios(c, b, calcular(b, c), meses)
    p = v.resumo.loc["presumido"]
    # lucros de ~R$ 150 mil/mês > R$ 50 mil → IRRF de 10% sobre o total distribuído
    perto(p["irrf_dividendos"], 0.10 * p["dividendos"])
    # renda > R$ 1,2 mi → IRPFM a 10%; redutor = lucros × máx(0, alíquota PJ + 10% − 34%)
    d = v.detalhe.set_index("regime").loc["presumido"]
    assert d["aliquota_irpfm"] == 0.10
    esperado = max(0.0, d["renda_anual"] * 0.10 - d["irrf_pro_labore"]
                   - d["dividendos"] * max(0.0, p["aliquota_pj"] + 0.10 - 0.34))
    perto(d["irpfm"], esperado)
    # INSS do sócio: 932,31 × 12
    perto(p["inss_socios"], 932.31 * 12, 0.05)
    assert v.resumo["melhor"].sum() == 1
    assert any("50.000" in o for o in v.observacoes)


def test_visao_socios_sem_cadastro():
    c = Cliente(nome="Sem sócios")
    b = base("2026-01", "2026-06", rec_anexo_iii=50_000)
    v = visao_socios(c, b, calcular(b, c), b.meses)
    assert v.vazia and "Cadastre os sócios" in v.observacoes[0]


# ---------------- pró-labore ótimo ----------------
def test_otimizador_fator_r():
    # 150 mil/mês com Fator R; salários 20 mil + FGTS 1,6 mil; pró-labore 6 mil → Fator R 15,3% (Anexo V)
    # pró-labore para 28%: 28% × 150.000 − 21.600 = 20.400/mês
    c = Cliente(nome="Engenharia", anexo_servico="fator_r", socios=[Socio("A", 0.5), Socio("B", 0.5)])
    b = base("2025-01", "2026-09", rec_fator_r=150_000, salarios=20_000, pro_labore=6_000, fgts=1_600,
             custos=20_000, despesas=30_000)
    o = otimizar_pro_labore(b, c, regimes=("simples", "presumido"), pontos=11)
    perto(o.para_fator_r, 20_400, 0.05)
    m = o.melhor.loc["simples"]
    assert m["pro_labore"] >= 20_400 and m["economia"] > 0
    assert o.grade.loc[o.grade.pro_labore == m["pro_labore"], "fator_r"].iloc[0] >= 0.28
    # FS12 hoje (21.600 + 6.000) × 12 = 331.200; falta 28% × 1,8 mi − 331.200 = 172.800 ÷ 14.400/mês = 12 meses
    assert o.meses_ate_anexo_iii == 12
    # no Presumido o pró-labore paga 20% patronal: o ótimo é o mínimo (1 salário mínimo por sócio)
    perto(o.melhor.loc["presumido", "pro_labore"], 2 * 1_621.00)


# ---------------- prazos ----------------
def test_dias_uteis_e_prazos():
    assert pascoa(2027) == dt.date(2027, 3, 28)
    assert ultimo_dia_util(2027, 1) == dt.date(2027, 1, 29)     # 30 e 31/01/2027 caem no fim de semana
    assert ultimo_dia_util(2027, 4) == dt.date(2027, 4, 30)
    c = Cliente(nome="X", regime_atual="presumido")
    pz = prazos(c, "simples", hoje=dt.date(2026, 10, 23))
    opcao = pz[pz.evento == "Opção pelo Simples Nacional"].iloc[0]
    assert opcao["data"] == dt.date(2027, 1, 29) and opcao["acao"] == "DECIDIR"
    assert pz["data"].is_monotonic_increasing
    assert (pz["data"] >= dt.date(2026, 10, 23)).all()


# ---------------- carteira ----------------
def test_carteira(tmp_path, monkeypatch, base_exemplo):
    monkeypatch.setenv("ZERA_DADOS", str(tmp_path / "dados"))
    com_base = Cliente(nome="Com Base", cnpj="11.111.111/0001-11", regime_atual="real", iss_aliquota=0.02)
    com_base.salvar()
    base_exemplo.salvar(com_base.pasta())
    sem_base = Cliente(nome="Sem Base", cnpj="22.222.222/0001-22")
    sem_base.salvar()
    df = analisar_carteira([com_base, sem_base])
    assert list(df.cliente) == ["Com Base", "Sem Base"]
    linha = df.iloc[0]
    assert linha.situacao in ("MUDAR", "AVALIAR", "MANTER")
    if linha.situacao == "MUDAR":
        assert linha.economia_ano > 0
    assert df.iloc[1].situacao == "SEM BASE"


def test_cliente_com_socios_salva_e_carrega(tmp_path, monkeypatch):
    monkeypatch.setenv("ZERA_DADOS", str(tmp_path / "dados"))
    c = Cliente(nome="Holding", socios=[Socio("Ana", 0.6, 5_000, 1), Socio("Bia", 0.4)], distribuicao_forma="anual")
    c2 = Cliente.carregar(c.salvar())
    assert c2.socios[0] == Socio("Ana", 0.6, 5_000, 1) and c2.distribuicao_forma == "anual"
