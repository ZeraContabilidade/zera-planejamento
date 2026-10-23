"""Reproduções independentes dos erros encontrados na revisão."""
import numpy as np
import pandas as pd
import pytest

from zera_planejamento.base import BaseMensal
from zera_planejamento.calculo import calcular
from zera_planejamento.equilibrio import _raizes
from zera_planejamento.projecao import projetar
from zera_planejamento.socios import visao_socios
from zera_planejamento.cliente import Socio
from zera_planejamento.regras.pessoa_fisica import irpfm


def test_sazonalidade_sem_receita_em_um_mes(cliente):
    # Dois anos completos, janeiro sem operação: 0/índice sazonal zero não pode virar NaN.
    idx = pd.period_range('2024-01', '2026-02', freq='M')
    b = BaseMensal.de_dataframe(pd.DataFrame({'rec_anexo_iii':
        [0. if p.month == 1 else 100000. for p in idx], 'custos': 20000.}, index=idx))
    for c in projetar(b, cliente).values():
        assert np.isfinite(c.base_projetada.dados['rec_anexo_iii']).all()
        assert c.base_projetada.receita_bruta().sum() > 0


def test_equilibrio_nao_confunde_indisponibilidade_com_raiz():
    # +infinito significa regime indisponível; não existe igualdade entre -100 e +infinito.
    assert _raizes(lambda x: -100. if x < 0.5 else np.inf, 0., 1.) == []
    assert _raizes(lambda x: -100. if x < 0.45 else (np.nan if x < 0.55 else 100.), 0., 1., passos=2) == []


def test_resumo_sem_meses_nao_recomenda_regime(base_exemplo, cliente):
    r = calcular(base_exemplo, cliente).resumo(pd.period_range('2040-01', '2040-06', freq='M'))
    assert not r.elegivel.any()
    assert not r.melhor.any()


def test_socios_sem_meses_nao_divide_por_zero(base_exemplo, cliente):
    cliente.socios = [Socio('Sócio')]
    r = calcular(base_exemplo, cliente)
    assert visao_socios(cliente, base_exemplo, r, pd.PeriodIndex([], freq='M')).vazia


def test_aliquota_pj_usa_lucro_antes_irpj_csll(base_exemplo, cliente):
    cliente.socios = [Socio('Sócio')]
    r = calcular(base_exemplo, cliente)
    v = visao_socios(cliente, base_exemplo, r, base_exemplo.meses)
    for regime in ('presumido', 'real'):
        tributos_renda = r.regimes[regime][['irpj', 'csll']].to_numpy().sum()
        lucro_liquido = v.resumo.at[regime, 'lucro_contabil']
        # Lei 9.250, art. 16-B, §3º, I/III: denominador antes dos tributos sobre renda.
        assert v.resumo.at[regime, 'aliquota_pj'] == pytest.approx(
            tributos_renda / (lucro_liquido + tributos_renda), abs=1e-12)


def test_redutor_usa_aliquota_incremental_pf():
    # Lei 9.250, art. 16-B, §3º, II. Com dividendos: 150 mil - 60 mil = 90 mil.
    # Sem dividendos: renda de 300 mil, imposto mínimo zero.
    # Alíquota incremental = 90/1.200 = 7,5%; redutor = 1,2 mi * (30%+7,5%-34%) = 42 mil.
    r = irpfm(1500000, 1200000, 60000, .30)
    assert r['redutor'] == pytest.approx(42000, abs=.01)
    assert r['devido'] == pytest.approx(48000, abs=.01)


def test_cache_nao_sobrevive_a_calculo(base_exemplo, cliente):
    primeiro = calcular(base_exemplo, cliente)
    base_exemplo.dados['pro_labore'] = 30000.
    segundo = calcular(base_exemplo, cliente)
    assert (segundo.regimes['presumido']['encargos'] > primeiro.regimes['presumido']['encargos']).all()


@pytest.mark.parametrize('pesos', [[-10., 0., 10.], [0., 0., 0.], [np.nan, 2., 3.]])
def test_rateio_preserva_pesos_e_nan(pesos):
    from zera_planejamento.calculo.comum import ratear
    p = pd.Series(pesos)
    positivos = p.clip(lower=0)
    esperado = (100 * positivos / positivos.sum()) if positivos.sum() > 0 else pd.Series(100 / len(p), index=p.index)
    pd.testing.assert_series_equal(ratear(100., p), esperado)


@pytest.mark.parametrize('periodo', ['anual', 'trimestral'])
def test_avaliador_margem_bate_motor_com_prejuizos(base_exemplo, cliente, periodo):
    from zera_planejamento.equilibrio import _avaliador_margem, _com_margem, _custo
    cliente.lr_periodo = periodo
    cliente.prejuizo_fiscal_inicial = 200000.
    cliente.base_negativa_inicial = 100000.
    meses = base_exemplo.meses[-6:]
    avaliar = _avaliador_margem(base_exemplo, cliente, meses)
    # Margens com prejuízo e lucro: testa transporte entre períodos e trava de compensação.
    for margem in (-.3, .1, .6):
        esperado = _custo('real', _com_margem(base_exemplo, meses, margem), cliente, meses)
        assert avaliar(margem) == pytest.approx(esperado, abs=.01, rel=0)


def test_equilibrio_nao_recomenda_dois_regimes_indisponiveis(base_exemplo, cliente, monkeypatch):
    from zera_planejamento import equilibrio
    cenario = projetar(base_exemplo, cliente)['Neutro']
    monkeypatch.setattr(equilibrio, '_custo', lambda *args: float('inf'))
    quadro = equilibrio.pontos_equilibrio(cenario, cliente).set_index('comparacao')
    assert 'indisponíveis' in quadro.at['Simples × Lucro Presumido', 'leitura']
