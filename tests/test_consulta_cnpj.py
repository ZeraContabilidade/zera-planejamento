"""Consulta do CNPJ (dados abertos da Receita): validação, leitura das duas fontes e reserva. Sem internet."""
import urllib.error

import pytest

from zera_planejamento import consulta_cnpj as cc

BRASILAPI = {
    "cnpj": "11222333000181", "razao_social": "EMPRESA TESTE LTDA", "nome_fantasia": "TESTE",
    "descricao_situacao_cadastral": "ATIVA", "data_inicio_atividade": "2019-03-01",
    "natureza_juridica": "Sociedade Empresária Limitada", "porte": "MICRO EMPRESA", "capital_social": 50000,
    "cnae_fiscal": 7112000, "cnae_fiscal_descricao": "Serviços de engenharia",
    "cnaes_secundarios": [{"codigo": 7119799, "descricao": "Atividades técnicas"}, {"codigo": 0, "descricao": ""}],
    "municipio": "SAO PAULO", "uf": "SP", "logradouro": "RUA A", "numero": "10", "bairro": "CENTRO", "cep": "01000000",
    "opcao_pelo_simples": False, "opcao_pelo_mei": False,
    "regime_tributario": [{"ano": 2024, "forma_de_tributacao": "LUCRO PRESUMIDO"},
                          {"ano": 2023, "forma_de_tributacao": "LUCRO REAL"}],
    "qsa": [{"nome_socio": "ANA SOUZA", "qualificacao_socio": "Sócio-Administrador", "identificador_de_socio": 2},
            {"nome_socio": "HOLDING X LTDA", "qualificacao_socio": "Sócio", "identificador_de_socio": 1}],
}
CNPJWS = {
    "razao_social": "EMPRESA TESTE LTDA", "capital_social": "50000.00",
    "porte": {"descricao": "Micro Empresa"}, "natureza_juridica": {"descricao": "Sociedade Empresária Limitada"},
    "simples": {"simples": "Sim", "mei": "Não", "data_opcao_simples": "2019-03-01"},
    "estabelecimento": {"cnpj": "11222333000181", "nome_fantasia": "TESTE", "situacao_cadastral": "Ativa",
                        "atividade_principal": {"id": "7112000", "descricao": "Serviços de engenharia"},
                        "cidade": {"nome": "São Paulo"}, "estado": {"sigla": "SP"}},
    "socios": [{"nome": "ANA SOUZA", "tipo": "Pessoa Física", "qualificacao_socio": {"descricao": "Sócio-Administrador "}}],
}


def test_validacao_cnpj():
    assert cc.cnpj_valido("11.222.333/0001-81")
    assert not cc.cnpj_valido("11.222.333/0001-82")      # dígito verificador errado
    assert not cc.cnpj_valido("11111111111111")           # todos iguais
    assert not cc.cnpj_valido("123")
    assert cc.formatar_cnpj("11222333000181") == "11.222.333/0001-81"


def test_leitura_brasilapi():
    d = cc.de_brasilapi(BRASILAPI)
    assert d.razao_social == "EMPRESA TESTE LTDA" and d.cnpj == "11.222.333/0001-81"
    assert d.atividade == "7112-0/00 — Serviços de engenharia"
    assert d.cnaes_secundarios == ["7119-7/99 — Atividades técnicas"]
    assert d.municipio == "Sao Paulo" and d.uf == "SP" and d.ativa
    # fora do Simples: vale a forma de tributação mais recente declarada
    assert d.ultima_tributacao == "LUCRO PRESUMIDO (2024)" and d.regime_sugerido() == "presumido"
    assert [s.pessoa_fisica for s in d.socios] == [True, False]


def test_leitura_cnpjws_optante_do_simples():
    d = cc.de_cnpjws(CNPJWS)
    assert d.simples is True and d.mei is False and d.regime_sugerido() == "simples"
    assert d.situacao == "ATIVA" and d.capital_social == 50_000.0
    assert d.socios[0].qualificacao == "Sócio-Administrador" and d.socios[0].pessoa_fisica


def test_consulta_usa_reserva_quando_brasilapi_falha(monkeypatch):
    def baixar(url, timeout):
        if "brasilapi" in url:
            raise urllib.error.URLError("fora do ar")
        return CNPJWS
    monkeypatch.setattr(cc, "_baixar", baixar)
    d = cc.consultar_cnpj("11.222.333/0001-81")
    assert d.fonte.startswith("CNPJ.ws") and d.consultado_em


def test_consulta_cnpj_invalido_ou_inexistente(monkeypatch):
    with pytest.raises(cc.ErroConsultaCNPJ, match="inválido"):
        cc.consultar_cnpj("11.222.333/0001-82")

    def nao_achou(url, timeout):
        raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)
    monkeypatch.setattr(cc, "_baixar", nao_achou)
    with pytest.raises(cc.ErroConsultaCNPJ, match="não encontrado"):
        cc.consultar_cnpj("11.222.333/0001-81")
