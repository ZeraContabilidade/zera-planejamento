"""Leitura dos relatórios do Domínio, De-Para e importação para a base mensal."""
import math

import pandas as pd
import pytest

from zera_planejamento.base import BaseMensal
from zera_planejamento.dominio import DePara, Regra, importar_relatorios, ler_relatorio
from zera_planejamento.dominio.leitura import numero, so_digitos


def test_conversoes():
    assert numero("1.621,00") == 1621.0 and numero("(10,00)") == -10.0 and numero("-") is None
    assert so_digitos(6552.0) == "6552" and so_digitos("35.173.223/0001-35") == "35173223000135"


def test_leitores(relatorios):
    s = ler_relatorio(relatorios["servicos"])
    assert s.tipo == "servicos" and len(s.dados) == 3 and s.dados.valor.sum() == 100000
    assert s.extras["total_geral"] == 100000 and s.cnpj == "11222333000181"
    e = ler_relatorio(relatorios["entradas"])
    assert e.tipo == "entradas" and len(e.dados) == 4          # cabeçalho repetido e subtotais ignorados
    assert e.dados.loc[e.dados.nota == "900", "imp_ipi"].iloc[0] == 120.0   # linha de continuação
    f = ler_relatorio(relatorios["folha"])
    assert f.tipo == "folha" and len(f.dados) == 6
    assert f.dados.groupby("categoria").base_inss.sum().to_dict() == {"contribuinte": 9000.0, "empregado": 7500.0}
    d = ler_relatorio(relatorios["dre"])
    assert d.tipo == "dre" and d.extras["acumulada_desde_janeiro"] and str(d.fim) == "2026-03-31"
    assert math.isclose(d.dados.saldo.sum(), d.extras["resultado_impresso"])


def test_depara_precedencia():
    dp = DePara([Regra("CFOP_ENTRADA", "2556", "cred_insumos", "uniformes"),
                 Regra("FORNECEDOR", "ROLAMENTOS", "cred_insumos")])
    assert dp.cfop("CFOP_ENTRADA", "2556")[0] == "cred_insumos"     # exato do cliente vence o padrão *556
    assert dp.cfop("CFOP_ENTRADA", "1556")[0] == "uso_consumo"      # padrão
    assert dp.cfop("CFOP_ENTRADA", "1407", "ROLAMENTOS CBF LTDA")[0] == "cred_insumos"
    assert dp.cfop("CFOP_ENTRADA", "2915")[0] == "IGNORAR"
    assert dp.conta_dre("1", "4.2.2.04.000020", "MULTAS FISCAIS")[0] == "despesa_indedutivel"
    assert dp.conta_dre("1", "4.2.2.01.000002", "PRÓ-LABORE")[0] == "FOLHA"
    assert dp.conta_dre("1", "4.1.6.01.000001", "CUSTOS")[0] == "custos"
    assert dp.vinculo("Diretor", "contribuinte") == "pro_labore" and dp.vinculo("Celetista", "empregado") == "salarios"
    assert DePara([Regra("XPTO", "1", "cred_insumos")]).invalidas


def test_importacao(relatorios, cliente):
    base = BaseMensal.vazia()
    imp = importar_relatorios(list(relatorios.values()), cliente, base)
    imp.aplicar(base)
    d = base.dados
    assert d.loc["2026-01", "rec_anexo_iii"] == 50000 and d["rec_anexo_iii"].sum() == 100000
    assert d.loc["2026-01", "cred_insumos"] == 8000 and d.loc["2026-03", "uso_consumo"] == 1000
    assert d.loc["2026-02", "cred_insumos"] == 0                      # mês coberto sem compra: zero, não vazio
    assert d["cred_servicos"].sum() == 3000
    assert d["pro_labore"].sum() == 9000 and d["salarios"].sum() == 7500 and d["fgts"].sum() == 600
    # DRE acumulada jan–mar dividida por 3; pessoal fica com o extrato; multa entra em despesas e adições
    assert math.isclose(d["custos"].sum(), 9000) and math.isclose(d["adicoes"].sum(), 300)
    assert math.isclose(d["despesas"].sum(), 6300) and math.isclose(d["receitas_financeiras"].sum(), 600)
    niveis = {a.nivel for a in imp.alertas.itens}
    assert "CRÍTICO" not in niveis
    textos = " ".join(a.mensagem for a in imp.alertas.itens)
    assert "CPF igual ao do empregado JOAO DA SILVA" in textos     # prestador = empregado
    assert "veio acumulada" in textos
    assert imp.cruzadas[0]["situacao"] == "OK"                        # receita notas × DRE


def test_cnpj_divergente_e_critico(relatorios):
    from zera_planejamento.cliente import Cliente
    outro = Cliente(nome="Outra", cnpj="99.888.777/0001-66")
    imp = importar_relatorios([relatorios["servicos"]], outro, BaseMensal.vazia())
    assert imp.alertas.contagem()["CRÍTICO"] == 1


def test_meses_fora_do_periodo_nao_mudam(relatorios, cliente):
    idx = pd.period_range("2025-12", "2026-04", freq="M")
    base = BaseMensal.de_dataframe(pd.DataFrame({"rec_anexo_iii": 1.0, "cred_aluguel": 500.0}, index=idx), "manual")
    importar_relatorios([relatorios["servicos"], relatorios["entradas"]], cliente, base).aplicar(base)
    assert base.dados.loc["2025-12", "rec_anexo_iii"] == 1.0 and base.dados.loc["2026-04", "rec_anexo_iii"] == 1.0
    assert base.dados.loc["2026-02", "cred_aluguel"] == 500.0   # aluguel digitado não é apagado pela importação
    assert base.origem.loc["2025-12", "rec_anexo_iii"] == "manual"
