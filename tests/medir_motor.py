"""Medição reproduzível: PYTHONPATH=src python tests/medir_motor.py.

Base sintética de 21 meses do conftest. Aquecimento separado, cinco execuções
do motor e três do fluxo completo, sem cache entre planejamentos.
"""
import json
import platform
import statistics
from time import perf_counter
import pandas as pd
import numpy as np
from conftest import base_exemplo, cliente
from zera_planejamento.calculo import calcular
from zera_planejamento.planejamento import gerar_planejamento


def medir():
    b, c = base_exemplo.__wrapped__(), cliente.__wrapped__()
    calcular(b, c)
    tempos = {}
    for nome, f, n in [('calcular', lambda: calcular(b, c), 5),
                        ('gerar_planejamento', lambda: gerar_planejamento(c, b), 3)]:
        valores = []
        for _ in range(n):
            inicio = perf_counter()
            f()
            valores.append(perf_counter() - inicio)
        tempos[nome] = {'segundos': valores, 'mediana': statistics.median(valores)}
        print(nome, tempos[nome], flush=True)
    tempos['ambiente'] = {'python': platform.python_version(), 'pandas': pd.__version__,
                          'numpy': np.__version__, 'plataforma': platform.platform()}
    return tempos


if __name__ == '__main__':
    print(json.dumps(medir(), ensure_ascii=False, indent=2))
