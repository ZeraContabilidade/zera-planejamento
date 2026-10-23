"""
Regressão com os relatórios reais da CS Geartech (jan–set/2026). Roda só onde existir
``amostras/cs_geartech/`` (fora do git). Valores conferidos à mão e contra o motor Excel v3:

- Presumido bate no centavo com o motor Excel (R$ 284.704,68).
- Simples difere do Excel porque o Excel aplicava a RBT12 defasada de 2027 aos meses de 2026;
  aqui cada competência usa a regra do seu ano (jan/26 confere: R$ 24.904,52).
- Real difere porque o Excel dava crédito de PIS/Cofins sobre uso e consumo e aluguel sem DRE.
"""
from pathlib import Path

import pandas as pd
import pytest

from zera_planejamento.base import BaseMensal
from zera_planejamento.calculo import calcular
from zera_planejamento.cliente import Cliente
from zera_planejamento.dominio import importar_relatorios

PASTA = Path(__file__).parents[1] / "amostras" / "cs_geartech"
pytestmark = [pytest.mark.amostras,
              pytest.mark.skipif(not (PASTA / "Servicos.xls").exists(), reason="amostras/cs_geartech ausente")]


@pytest.fixture(scope="module")
def caso():
    c = Cliente(nome="CS GEARTECH MANUTENCAO E INSPECAO DE REDUTORES LTDA", cnpj="35.173.223/0001-35",
                iss_aliquota=0.02, rat=0.02, fap=1.0, terceiros=0.058)
    base = BaseMensal.vazia()
    hist = PASTA / "historico_2025.csv"
    if hist.exists():
        h = pd.read_csv(hist, sep=";", index_col=0)
        h.index = pd.PeriodIndex(h.index, freq="M")
        base.mesclar(h, "histórico 2025")
    imp = importar_relatorios(sorted(PASTA.glob("*.xls")), c, base)
    imp.aplicar(base)
    return c, base, imp


def test_importacao_totais(caso):
    _, base, imp = caso
    d = base.dados.loc["2026-01":"2026-09"]
    assert round(d.rec_anexo_iii.sum(), 2) == 1_702_112.28
    assert round(d.pro_labore.sum(), 2) == 43_767.00 and round(d.salarios.sum(), 2) == 6_207.03
    assert round(d.fgts.sum(), 2) == 496.55
    assert round(d.imobilizado.sum(), 2) == 199_218.20
    assert imp.alertas.contagem()["CRÍTICO"] == 0
    assert any("CPF igual ao do empregado ANTONIO" in a.mensagem for a in imp.alertas.itens)


def test_regimes(caso):
    c, base, _ = caso
    if not (PASTA / "historico_2025.csv").exists():
        pytest.skip("sem historico_2025.csv")
    r = calcular(base, c).resumo(pd.period_range("2026-01", "2026-09", freq="M"))
    assert round(r.at["presumido", "tributos"], 2) == 284_704.68
    assert round(r.at["simples", "tributos"], 2) == 237_945.88
    assert round(r.at["real", "tributos"], 2) == 574_294.06
