"""Foto anterior à otimização: dados sintéticos, estruturas e valores completos.

Para gerar deliberadamente uma nova referência: python tests/test_foto_motor.py --gravar.
Não executar esse comando para aceitar automaticamente uma regressão.
"""
import ast
import dataclasses
import json
import math
import sys
from pathlib import Path
from time import perf_counter

import numpy as np
import pandas as pd
import pytest

from zera_planejamento.base import BaseMensal
from zera_planejamento.calculo import calcular
from zera_planejamento.cliente import Cliente, Socio
from zera_planejamento.planejamento import gerar_planejamento
from conftest import base_exemplo, cliente
from test_calculo import CLIENTE, base

ARQUIVO = Path(__file__).with_name('foto_motor.json')


def casos():
    yield 'conftest_21_meses', base_exemplo.__wrapped__(), cliente.__wrapped__()
    # Extrai todas as chamadas literais ao construtor das bases do teste original.
    arvore = ast.parse(Path(__file__).with_name('test_calculo.py').read_text(encoding='utf-8'))
    for i, no in enumerate(n for n in ast.walk(arvore) if isinstance(n, ast.Call)
                           and isinstance(n.func, ast.Name) and n.func.id == 'base'):
        args = [ast.literal_eval(a) for a in no.args]
        kwargs = {k.arg: ast.literal_eval(k.value) for k in no.keywords}
        cli = CLIENTE
        if 'rec_anexo_i' in kwargs:
            cli = Cliente(nome='R', regime_atual='presumido', rat=0, terceiros=0, fap=0)
        yield f'calculo_{i}', base(*args, **kwargs), cli
    idx = pd.period_range('2026-01', '2026-06', freq='M')
    df = pd.DataFrame({'rec_anexo_iii': [0, 0, 0, 100000, 100000, 100000],
                       'despesas': [100000, 100000, 100000, 0, 0, 0],
                       'iss': 0., 'icms_debito': 0., 'icms_credito': 0.}, index=idx)
    yield 'compensacao_prejuizo', BaseMensal.de_dataframe(df), Cliente(nome='R', regime_atual='presumido', rat=0, terceiros=0)
    cli = cliente.__wrapped__()
    cli.socios = [Socio('Sócio sintético', participacao=100)]
    yield 'conftest_com_socio', base_exemplo.__wrapped__(), cli


def serializar(obj):
    if isinstance(obj, pd.DataFrame):
        return {'indice': [str(x) for x in obj.index], 'colunas': list(obj.columns),
                'dados': [[serializar(x) for x in linha] for linha in obj.to_numpy()]}
    if isinstance(obj, (pd.Index, pd.Series, np.ndarray)):
        return [serializar(x) for x in obj]
    if dataclasses.is_dataclass(obj):
        # Prazos usam a data do sistema e pendências são textos de aviso; não são resultados do motor.
        # Gerado_em é volátil.
        return {f.name: serializar(getattr(obj, f.name)) for f in dataclasses.fields(obj)
                if f.name not in ('gerado_em', 'prazos', 'pendencias')}
    if isinstance(obj, dict):
        return {str(k): serializar(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [serializar(x) for x in obj]
    if isinstance(obj, (float, np.floating)):
        return float(obj) if math.isfinite(obj) else str(obj)
    if isinstance(obj, np.generic):
        return obj.item()
    if isinstance(obj, pd.Period):
        return str(obj)
    return obj


def comparar(atual, foto, caminho='', tolerancia=.01):
    if isinstance(foto, dict):
        if caminho.endswith('/cliente'):
            # Campos de cadastro criados depois da foto (ex.: mapa_rotulos) não entram no cálculo; só são
            # aceitos se estiverem vazios. Os demais campos e todos os valores continuam comparados.
            novos = {k: v for k, v in atual.items() if k not in foto}
            assert all(v in ({}, [], '', None) for v in novos.values()), (caminho, novos)
            atual = {k: v for k, v in atual.items() if k in foto}
        assert atual.keys() == foto.keys(), caminho
        if set(foto) == {'indice', 'colunas', 'dados'}:
            assert atual['indice'] == foto['indice'], caminho
            assert atual['colunas'] == foto['colunas'], caminho
            assert len(atual['dados']) == len(foto['dados']), caminho
            for i, (linha, referencia) in enumerate(zip(atual['dados'], foto['dados'])):
                assert len(linha) == len(referencia), caminho
                for col, a, b in zip(foto['colunas'], linha, referencia):
                    # carga_total é monetária; carga e carga_pct são razões.
                    razao = col.startswith(('aliq', 'fator', 'participacao')) or col in ('carga', 'carga_pct')
                    tol = 1e-10 if razao else .01
                    comparar(a, b, f'{caminho}/{i}/{col}', tol)
            return
        for k in foto:
            comparar(atual[k], foto[k], f'{caminho}/{k}')
    elif isinstance(foto, list):
        assert len(atual) == len(foto), caminho
        for i, (a, b) in enumerate(zip(atual, foto)):
            comparar(a, b, f'{caminho}/{i}')
    elif isinstance(foto, (int, float)) and not isinstance(foto, bool):
        assert atual == pytest.approx(foto, abs=tolerancia, rel=0), caminho
    else:
        assert atual == foto, caminho


@pytest.mark.parametrize('nome,b,cli', list(casos()), ids=lambda x: x if isinstance(x, str) else None)
def test_foto_motor(nome, b, cli):
    foto = json.loads(ARQUIVO.read_text(encoding='utf-8'))[nome]
    if nome == 'conftest_com_socio':
        # Exceção legal explícita, sem regravar a foto original: Lei 9.250/1995,
        # art. 16-B, §3º, I/III (Lei 15.270/2025). IR/(lucro líquido+IR).
        # A foto anterior guardava a=IR/lucro líquido; a corrigida é a/(1+a).
        resumo = foto['planejamento']['socios']['resumo']
        coluna = resumo['colunas'].index('aliquota_pj')
        for regime in ('presumido', 'real'):
            linha = resumo['dados'][resumo['indice'].index(regime)]
            linha[coluna] = linha[coluna] / (1 + linha[coluna])
    foto['planejamento'].pop('pendencias', None)   # textos de aviso (pendências [CONFERIR]) não são resultados
    comparar(serializar(calcular(b, cli)), foto['calcular'])
    comparar(serializar(gerar_planejamento(cli, b)), foto['planejamento'])


if __name__ == '__main__':
    if '--gravar' not in sys.argv:
        raise SystemExit('Use pytest para verificar; --gravar apenas para criar a referência.')
    fotos = {}
    for nome, b, cli in casos():
        inicio = perf_counter()
        r = calcular(b, cli)
        motor = perf_counter() - inicio
        inicio = perf_counter()
        p = gerar_planejamento(cli, b)
        tempo = perf_counter() - inicio
        fotos[nome] = {'calcular': serializar(r), 'planejamento': serializar(p)}
        print(f'{nome}: calcular={motor:.6f}s planejamento={tempo:.6f}s', flush=True)
    ARQUIVO.write_text(json.dumps(fotos, ensure_ascii=False, indent=1), encoding='utf-8')


def test_tolerancia_da_foto_distingue_reais_de_aliquotas():
    # Um centavo é a tolerância monetária; razões mantêm precisão de 1e-10.
    foto = {'indice': ['real'], 'colunas': ['carga_total', 'carga_pct'],
            'dados': [[214507.31628440367, .25]]}
    comparar({'indice': ['real'], 'colunas': foto['colunas'],
              'dados': [[214507.3162844038, .25]]}, foto)
    with pytest.raises(AssertionError):
        comparar({'indice': ['real'], 'colunas': foto['colunas'],
                  'dados': [[214507.34, .25]]}, foto)
    with pytest.raises(AssertionError):
        comparar({'indice': ['real'], 'colunas': foto['colunas'],
                  'dados': [[214507.31628440367, .25001]]}, foto)
