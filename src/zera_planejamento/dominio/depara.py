"""
De-Para: para onde vai cada valor dos relatórios do Domínio na base mensal.

As regras do cliente (``Cliente.depara``) valem antes das regras padrão abaixo.

Tipos de regra
--------------
CFOP_ENTRADA / CFOP_SAIDA  chave = CFOP exato (1556) ou final (*556). Exato vence o final.
ACUMULADOR_SERVICO          chave = código do acumulador do Domínio ou * (todos).
FORNECEDOR                  chave = trecho do nome do fornecedor (vence o CFOP nas entradas).
DRE_CONTA                   chave = classificação completa ou código reduzido. Vence tudo na DRE.
DRE_PALAVRA                 chave = trecho da descrição (a primeira que bater, na ordem).
DRE_GRUPO                   chave = início da classificação (ex. 4.1). Vale o mais longo.
FOLHA_VINCULO               chave = trecho do vínculo (Diretor, Celetista...) ou *empregado / *contribuinte.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

from ..base import COLUNAS
from .leitura import normalizar

ESPECIAIS = {
    "SERVICO_PADRAO": "Serviço (anexo do cadastro do cliente)",
    "despesa_indedutivel": "Despesa indedutível (entra em despesas e em adições)",
    "FOLHA": "Pessoal (vem do extrato da folha)",
    "RECEITA": "Receita (só conferência)",
    "IGNORAR": "Ignorar",
    "NAO_CLASSIFICADO": "Não classificado (fica fora e gera alerta)",
}
DESTINOS: dict[str, str] = {**{c: d for c, (_, d) in COLUNAS.items()}, **ESPECIAIS}
TIPOS = ["CFOP_ENTRADA", "CFOP_SAIDA", "ACUMULADOR_SERVICO", "FORNECEDOR", "DRE_CONTA", "DRE_PALAVRA",
         "DRE_GRUPO", "FOLHA_VINCULO"]


@dataclass
class Regra:
    tipo: str
    chave: str
    destino: str
    obs: str = ""


def _suf(tipo, sufixos, destino, obs=""):
    return [Regra(tipo, f"*{s}", destino, obs) for s in sufixos]


PADRAO: list[Regra] = [
    Regra("ACUMULADOR_SERVICO", "*", "SERVICO_PADRAO", "Todas as notas de serviço vão para o anexo do cadastro"),
    # ---------------- Entradas ----------------
    *_suf("CFOP_ENTRADA", ["101", "102", "111", "113", "116", "117", "118", "120", "121", "122", "124", "125",
                           "126", "128", "401", "403", "651", "652", "653"], "cred_insumos",
          "Compra de mercadoria/insumo/combustível"),
    *_suf("CFOP_ENTRADA", ["251", "252", "253", "254", "255", "256", "257"], "cred_energia"),
    *_suf("CFOP_ENTRADA", ["351", "352", "353", "354", "355", "356", "357", "358", "359", "360", "932"],
          "cred_fretes", "Aquisição de serviço de transporte"),
    Regra("CFOP_ENTRADA", "*933", "cred_servicos", "Serviço tomado sujeito ao ISS"),
    *_suf("CFOP_ENTRADA", ["301", "302", "303", "304", "305", "306", "407", "556"], "uso_consumo",
          "Sem crédito de PIS/Cofins; com crédito de CBS/IBS a partir de 2027"),
    *_suf("CFOP_ENTRADA", ["406", "551"], "imobilizado", "PIS/Cofins via depreciação; CBS/IBS na aquisição"),
    *_suf("CFOP_ENTRADA", ["201", "202", "203", "204", "208", "209", "410", "411"], "devolucoes",
          "Devolução de venda: reduz a receita do mês"),
    *_suf("CFOP_ENTRADA", ["151", "152", "153", "154", "408", "409", "552", "553", "554", "555", "557", "658",
                           "659", "660", "661", "662", "663", "664"], "IGNORAR", "Transferência/devolução"),
    *_suf("CFOP_ENTRADA", ["901", "902", "903", "904", "905", "906", "907", "908", "909", "910", "911", "912",
                           "913", "914", "915", "916", "917", "918", "919", "920", "921", "922", "923", "924",
                           "925", "926", "931", "934", "949"], "IGNORAR",
          "Remessa/retorno (conserto, comodato, demonstração...): não é compra"),
    # ---------------- Saídas ----------------
    *_suf("CFOP_SAIDA", ["101", "103", "105", "109", "111", "116", "118", "122", "124", "125", "401", "402"],
          "rec_anexo_ii", "Venda de produção própria"),
    *_suf("CFOP_SAIDA", ["102", "104", "106", "110", "115", "117", "119", "120", "123", "403", "405"],
          "rec_anexo_i", "Revenda (403/405 com ST: segregar no PGDAS-D)"),
    *_suf("CFOP_SAIDA", ["933", "932"], "SERVICO_PADRAO"),
    *_suf("CFOP_SAIDA", ["201", "202", "410", "411", "413", "553", "556", "551", "552", "557", "151", "152",
                         "153", "155", "156"], "IGNORAR", "Devolução de compra, transferência, venda de ativo"),
    *_suf("CFOP_SAIDA", ["901", "902", "903", "904", "905", "906", "907", "908", "909", "910", "911", "912",
                         "913", "914", "915", "916", "917", "920", "921", "924", "925"], "IGNORAR", "Remessa/retorno"),
    # ---------------- DRE ----------------
    Regra("DRE_PALAVRA", "SIMPLES NACIONAL", "IGNORAR", "Tributo que o sistema recalcula"),
    Regra("DRE_PALAVRA", "IMPOSTO DE RENDA", "IGNORAR", "Tributo que o sistema recalcula"),
    Regra("DRE_PALAVRA", "CONTRIBUICAO SOCIAL", "IGNORAR", "Tributo que o sistema recalcula"),
    *[Regra("DRE_PALAVRA", p, "FOLHA") for p in ("PRO-LABORE", "PRO LABORE", "MAO-DE-OBRA", "MAO DE OBRA",
                                                   "DESPESAS COM PESSOAL", "SALARIO", "FERIAS", "13O", "FGTS")],
    Regra("DRE_PALAVRA", "INSS", "IGNORAR", "Encargo que o sistema recalcula por regime"),
    Regra("DRE_PALAVRA", "MULTA", "despesa_indedutivel", "Multa punitiva é indedutível"),
    Regra("DRE_PALAVRA", "BRINDE", "despesa_indedutivel", "Lei 9.249/95, art. 13, VII"),
    Regra("DRE_GRUPO", "3.1.1", "RECEITA", "Receita vem das notas"),
    Regra("DRE_GRUPO", "3.1.2", "IGNORAR", "Deduções da receita (tributos do regime atual)"),
    Regra("DRE_GRUPO", "3.1.3", "receitas_financeiras"),
    Regra("DRE_GRUPO", "4.1", "custos"),
    Regra("DRE_GRUPO", "4.2", "despesas"),
    # ---------------- Folha ----------------
    *[Regra("FOLHA_VINCULO", v, "pro_labore") for v in ("diretor", "socio", "titular", "autonomo")],
    Regra("FOLHA_VINCULO", "estagi", "IGNORAR", "Bolsa de estágio não é salário"),
    Regra("FOLHA_VINCULO", "*empregado", "salarios"),
    Regra("FOLHA_VINCULO", "*contribuinte", "pro_labore"),
]


class DePara:
    def __init__(self, regras_cliente: list[Regra] | None = None, coluna_servico: str = "rec_anexo_iii"):
        self.cliente = list(regras_cliente or [])
        self.regras = self.cliente + PADRAO
        self.coluna_servico = coluna_servico
        self.invalidas = [r for r in self.cliente if r.destino not in DESTINOS or r.tipo not in TIPOS]
        self.regras = [r for r in self.regras if r not in self.invalidas]

    @classmethod
    def do_cliente(cls, cliente) -> "DePara":
        regras = [Regra(**{k: v for k, v in d.items() if k in ("tipo", "chave", "destino", "obs")})
                  for d in cliente.depara]
        return cls(regras, cliente.coluna_servico)

    @staticmethod
    def para_dicts(regras: list[Regra]) -> list[dict]:
        return [asdict(r) for r in regras]

    def _resolver(self, destino: str) -> str:
        return self.coluna_servico if destino == "SERVICO_PADRAO" else destino

    def cfop(self, tipo: str, cfop: str, fornecedor: str = "") -> tuple[str, str]:
        if fornecedor and tipo == "CFOP_ENTRADA":
            nome = normalizar(fornecedor)
            for r in self.regras:
                if r.tipo == "FORNECEDOR" and normalizar(r.chave) in nome:
                    return self._resolver(r.destino), f"fornecedor '{r.chave}'"
        for chave in (cfop, f"*{cfop[1:]}"):
            for r in self.regras:
                if r.tipo == tipo and r.chave == chave:
                    return self._resolver(r.destino), chave
        return "NAO_CLASSIFICADO", "-"

    def acumulador(self, codigo: str) -> str:
        for chave in (codigo, "*"):
            for r in self.regras:
                if r.tipo == "ACUMULADOR_SERVICO" and r.chave == chave:
                    return self._resolver(r.destino)
        return self.coluna_servico

    def conta_dre(self, codigo: str, classificacao: str, descricao: str) -> tuple[str, str]:
        for r in self.regras:
            if r.tipo == "DRE_CONTA" and r.chave in (codigo, classificacao):
                return r.destino, f"conta {r.chave}"
        desc = normalizar(descricao).upper()
        for r in self.regras:
            if r.tipo == "DRE_PALAVRA" and normalizar(r.chave).upper() in desc:
                return r.destino, f"palavra '{r.chave}'"
        grupos = [r for r in self.regras if r.tipo == "DRE_GRUPO"
                  and (classificacao == r.chave or classificacao.startswith(r.chave + "."))]
        if grupos:
            g = max(grupos, key=lambda r: len(r.chave))
            return g.destino, f"grupo {g.chave}"
        return "NAO_CLASSIFICADO", "-"

    def vinculo(self, vinculo: str, categoria: str) -> str:
        v = normalizar(vinculo)
        for r in self.regras:
            if r.tipo == "FOLHA_VINCULO" and not r.chave.startswith("*") and normalizar(r.chave) in v:
                return r.destino
        for r in self.regras:
            if r.tipo == "FOLHA_VINCULO" and r.chave == f"*{categoria}":
                return r.destino
        return "salarios" if categoria == "empregado" else "pro_labore"
