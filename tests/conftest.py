"""
Fixtures: relatórios sintéticos no layout do Domínio (sem dados de cliente) e uma base de exemplo.

Os layouts reproduzem o que o Domínio exporta: cabeçalho da empresa, título, cabeçalho de colunas
repetido por página, subtotais "Total CFOP"/"Total Geral", linhas de continuação de imposto e,
na folha, blocos por competência com rótulos "Rótulo:" seguidos do valor.
"""
import datetime as dt

import openpyxl
import pandas as pd
import pytest

from zera_planejamento.base import BaseMensal
from zera_planejamento.cliente import Cliente

CNPJ = "11222333000181"


def _salvar(linhas, caminho):
    wb = openpyxl.Workbook()
    ws = wb.active
    for r in linhas:
        ws.append(r)
    wb.save(caminho)
    return caminho


@pytest.fixture
def relatorios(tmp_path):
    vazio = [None] * 4
    servicos = [
        ["EMPRESA TESTE LTDA", None, None, None, None, None, None, None, None, None, "Página:", 1],
        ["CNPJ:", CNPJ], ["Insc Est.:", "123"], ["Período:", "01/01/2026 até 31/03/2026"],
        ["ACOMPANHAMENTO DE SERVIÇOS"],
        ["Código", "Data", "Nota", "Série", "Espécie", "Código", "Cliente", "AC.", "UF", "Valor Contábil", "Tipo",
         "Base Cálculo", "Alíq.", "Valor", "Isentas", "Outras"],
        [1, dt.datetime(2026, 1, 10), 101, None, 39, 5, "CLIENTE A", 6552, "SP", 50000.0, None, 0, 0, 0, 0, 0],
        [2, dt.datetime(2026, 2, 10), 102, None, 39, 6, "CLIENTE B", 6552, "SP", 30000.0, None, 0, 0, 0, 0, 0],
        [3, dt.datetime(2026, 3, 15), 103, None, 39, 5, "CLIENTE A", 6552, "SP", 20000.0, None, 0, 0, 0, 0, 0],
        ["Total Geral"], [None] * 9 + [100000.0],
    ]
    entradas = [
        ["EMPRESA TESTE LTDA"], ["CNPJ:", CNPJ], ["Insc Est.:", "123"], ["Período:", "01/01/2026 até 31/03/2026"],
        ["ACOMPANHAMENTO DE ENTRADAS"],
        ["Código", "Data", "Nota", "Série", "Espécie", "Código", "Fornecedor", "CFOP", "AC.", "UF", "Valor Contábil",
         "Tipo", "Base Cálculo", "Alíq.", "Valor", "Isentas", "Outras"],
        [1, dt.datetime(2026, 1, 5), 900, 1, 36, 9, "FORNECEDOR PECAS LTDA", 1102, 1151, "SP", 8000.0, "ICMS", 0, 0, 0, 0, 0],
        [None] * 11 + ["IPI", 0, 0, 120.0, 0, 0],
        ["Total CFOP"], [None] * 10 + [8000.0],
        [2, dt.datetime(2026, 2, 6), 901, 1, 36, 10, "CLIENTE A INDUSTRIA", 2915, 1920, "PR", 500000.0, None, 0, 0, 0, 0, 0],
        ["ACOMPANHAMENTO DE ENTRADAS"],
        ["Código", "Data", "Nota", "Série", "Espécie", "Código", "Fornecedor", "CFOP", "AC.", "UF", "Valor Contábil",
         "Tipo", "Base Cálculo", "Alíq.", "Valor", "Isentas", "Outras"],
        [3, dt.datetime(2026, 3, 7), 902, 1, 36, 11, "PAPELARIA LTDA", 1556, 1506, "SP", 1000.0, None, 0, 0, 0, 0, 0],
        [4, dt.datetime(2026, 3, 8), 77, 1, 36, 12, "JOAO DA SILVA 12345678909", 1933, 2101, "SP", 3000.0, None, 0, 0, 0, 0, 0],
        ["Total Geral"], [None] * 10 + [512000.0],
    ]
    folha = [["Empresa:", "1 - EMPRESA TESTE LTDA"], ["CNPJ:", CNPJ], ["Cálculo:", "Folha Mensal e Complementar"]]
    for mes in (1, 2, 3):
        folha += [["Competência:", dt.datetime(2026, mes, 1)], ["EXTRATO MENSAL"],
                  ["Contr:", 1, "SOCIO UM", "Situação:", "Trabalhando", "CPF:", "111.111.111-11"],
                  ["Vínculo:", "Diretor"],
                  [None, 9380, "PRO-LABORE DIAS", "30,00", "3.000,00", "P"],
                  ["ND:", 0, "Proventos:", 3000.0, "Descontos:", 330.0],
                  ["NF:", 0, "Base INSS:", 3000.0, "Base FGTS:", 0.0, "Valor FGTS:", 0.0],
                  ["Empr.:", 2, "JOAO DA SILVA", "Situação:", "Trabalhando", "CPF:", "123.456.789-09"],
                  ["Vínculo:", "Celetista"],
                  ["ND:", 0, "Proventos:", 2500.0, "Descontos:", 200.0],
                  ["NF:", 0, "Base INSS:", 2500.0, "Base FGTS:", 2500.0, "Valor FGTS:", 200.0],
                  ["Total Geral Proventos:", 5500.0]]
    dre = [
        ["Empresa:", "EMPRESA TESTE LTDA"], ["C.N.P.J.:", "11.222.333/0001-81"],
        ["DEMONSTRAÇÃO DO RESULTADO DO EXERCÍCIO EM 31/03/2026"],
        ["Código", "Classificação", "Descrição", "Saldo", "Soma", "Total"],
        [None, None, "RECEITA BRUTA"],
        [411, "3.1.1.02.000001", "SERVIÇOS PRESTADOS", 100000.0],
        [480, "3.1.2.03.000008", "(-) SIMPLES NACIONAL", -12000.0],
        [467, "4.1.6.01.000001", "CUSTOS DOS SERVIÇOS PRESTADOS", -9000.0],
        [297, "4.2.1.01", "DESPESAS COM PESSOAL", -7500.0],
        [332, "4.2.2.01.000002", "PRÓ-LABORE", -9000.0],
        [533, "4.2.2.04.000016", "MATERIAIS DE CONSUMO", -6000.0],
        [600, "4.2.2.04.000020", "MULTAS FISCAIS", -300.0],
        [432, "3.1.3.01.000001", "JUROS DE APLICAÇÕES", 600.0],
        [None, None, "LUCRO LÍQUIDO DO EXERCÍCIO", None, None, 56800.0],
    ]
    return {"servicos": _salvar(servicos, tmp_path / "Servicos.xlsx"), "entradas": _salvar(entradas, tmp_path / "Entradas.xlsx"),
            "folha": _salvar(folha, tmp_path / "Folha.xlsx"), "dre": _salvar(dre, tmp_path / "DRE.xlsx")}


@pytest.fixture
def cliente():
    return Cliente(nome="Empresa Teste Ltda", cnpj="11.222.333/0001-81", iss_aliquota=0.02)


@pytest.fixture
def base_exemplo():
    idx = pd.period_range("2025-01", "2026-09", freq="M")
    n = len(idx)
    df = pd.DataFrame({"rec_anexo_iii": [80000 + 2000 * i for i in range(n)], "salarios": 15000.0, "pro_labore": 6000.0,
                       "fgts": 1200.0, "custos": 12000.0, "despesas": 25000.0, "cred_insumos": 8000.0,
                       "receitas_financeiras": 500.0}, index=idx)
    return BaseMensal.de_dataframe(df, "exemplo")
