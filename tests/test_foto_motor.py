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
        # Prazos usam a data do sistema; não são resultados do motor. Gerado_em é volátil.
        return {f.name: serializar(getattr(obj, f.name)) for f in dataclasses.fields(obj)
                if f.name not in ('gerado_em', 'prazos')}
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


def comparar(atual, foto, caminho=''):
    if isinstance(foto, dict):
        assert atual.keys() == foto.keys(), caminho
        for k in foto:
            comparar(atual[k], foto[k], f'{caminho}/{k}')
    elif isinstance(foto, list):
        assert len(atual) == len(foto), caminho
        for i, (a, b) in enumerate(zip(atual, foto)):
            comparar(a, b, f'{caminho}/{i}')
    elif isinstance(foto, (int, float)) and not isinstance(foto, bool):
        assert atual == pytest.approx(foto, abs=0.01, rel=0), caminho
    else:
        assert atual == foto, caminho


@pytest.mark.parametrize('nome,b,cli', list(casos()), ids=lambda x: x if isinstance(x, str) else None)
def test_foto_motor(nome, b, cli):
    foto = json.loads(ARQUIVO.read_text(encoding='utf-8'))[nome]
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
