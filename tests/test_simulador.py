"""Simulador “E se…” e navegação pela Mesa do escritório."""
import math
from pathlib import Path

import pandas as pd

from zera_planejamento.base import BaseMensal
from zera_planejamento.cliente import Cliente
from zera_planejamento.simulador import Ajustes, aplicar, ano_base, simular


def perto(a, b, tol=0.01):
    assert math.isclose(a, b, abs_tol=tol), f"{a:,.2f} != {b:,.2f}"


def base_eng():
    # serviços com Fator R: R$ 150 mil/mês, salários 20 mil, FGTS 1,6 mil, pró-labore 6 mil → FS12 27,6 mil × 12
    idx = pd.period_range("2025-01", "2026-09", freq="M")
    return BaseMensal.de_dataframe(pd.DataFrame({
        "rec_fator_r": 150_000.0, "salarios": 20_000.0, "pro_labore": 6_000.0, "fgts": 1_600.0, "custos": 30_000.0,
        "despesas": 25_000.0}, index=idx))


CLI = Cliente(nome="Engenharia Exemplo", anexo_servico="fator_r", rat=0.0, terceiros=0.0)


def test_sem_ajuste_simulado_igual_ao_base():
    comp, meses = ano_base(base_eng(), CLI)
    assert len(meses) == 12 and str(meses[0]) == "2026-10"
    r = simular(comp, meses, CLI, Ajustes())
    pd.testing.assert_series_equal(r["base"]["tributos"], r["simulado"]["tributos"])


def test_ajustes_mexem_so_nos_meses_projetados():
    comp, meses = ano_base(base_eng(), CLI)
    sim = aplicar(comp, meses, Ajustes(receita=0.10, folha=-0.20, custos=0.10, pro_labore=25_000))
    d0, d1 = comp.dados, sim.dados
    m = meses[0]
    # receita × 1,10; custos acompanham a receita e ainda sobem 10%: × 1,10 × 1,10; despesas só × 1,10
    perto(d1.at[m, "rec_fator_r"], d0.at[m, "rec_fator_r"] * 1.10)
    perto(d1.at[m, "custos"], d0.at[m, "custos"] * 1.10 * 1.10)
    perto(d1.at[m, "despesas"], d0.at[m, "despesas"] * 1.10)
    perto(d1.at[m, "salarios"], d0.at[m, "salarios"] * 0.80)
    assert d1.at[m, "pro_labore"] == 25_000
    # histórico intacto
    pd.testing.assert_frame_equal(d0.loc[:"2026-09"], d1.loc[:"2026-09"])


def test_pro_labore_maior_sobe_o_fator_r_e_receita_maior_sobe_o_imposto():
    comp, meses = ano_base(base_eng(), CLI)
    r = simular(comp, meses, CLI, Ajustes(pro_labore=25_000))
    # Fator R base ≈ 27.600 ÷ 150.000 = 18,4%; com 25 mil de pró-labore a FS12 sobe a cada mês projetado
    perto(r["fator_r_base"], 27_600 / 150_000, 1e-6)
    assert r["fator_r_simulado"] > 0.28
    r2 = simular(comp, meses, CLI, Ajustes(receita=0.30))
    perto(r2["receita_simulado"], r2["receita_base"] * 1.30, 0.05)
    for reg in ("simples", "presumido"):
        assert r2["simulado"].at[reg, "tributos"] > r2["base"].at[reg, "tributos"]


def test_mesa_abre_o_dashboard_do_cliente_clicado(tmp_path, monkeypatch, base_exemplo):
    from streamlit.testing.v1 import AppTest

    import zera_planejamento.app as app_pkg
    monkeypatch.setenv("ZERA_DADOS", str(tmp_path / "dados"))
    a = Cliente(nome="Alfa Serviços", cnpj="11.222.333/0001-81", iss_aliquota=0.02)
    b = Cliente(nome="Beta Comércio", cnpj="11.444.777/0001-61")
    for c in (a, b):
        c.salvar()
    base_exemplo.salvar(b.pasta())
    at = AppTest.from_file(str(Path(app_pkg.__file__).parent / "main.py"), default_timeout=180)
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    botao = next(x for x in at.button if x.key == f"abrir_{b.id}")
    botao.click().run()
    assert not at.exception, [e.message for e in at.exception]
    assert at.session_state["cliente_id"] == b.id and at.session_state["sel_cliente"] == b.id
