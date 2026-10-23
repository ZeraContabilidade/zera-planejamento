"""
Consulta dos dados cadastrais do CNPJ na base pública da Receita Federal.

A consulta oficial da RFB exige certificado ou contrato (Serpro); aqui usamos serviços gratuitos que
republicam os **dados abertos do CNPJ da Receita Federal**:

1. BrasilAPI  — https://brasilapi.com.br/api/cnpj/v1/{cnpj}
2. CNPJ.ws    — https://publica.cnpj.ws/cnpj/{cnpj}   (reserva, se a primeira falhar)

Só o número do CNPJ sai do computador. Os dados podem ter alguns dias de atraso em relação ao
cadastro da Receita: conferir o cartão CNPJ em caso de dúvida.

O regime sugerido usa a opção pelo Simples (vigente) e, fora dele, a última forma de tributação
declarada (Lucro Real / Presumido) que a BrasilAPI informa.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field

FONTES = ("brasilapi", "cnpjws")
URL = {"brasilapi": "https://brasilapi.com.br/api/cnpj/v1/{}", "cnpjws": "https://publica.cnpj.ws/cnpj/{}"}
FORMA_PARA_REGIME = {"LUCRO REAL": "real", "LUCRO PRESUMIDO": "presumido", "LUCRO ARBITRADO": "presumido"}


class ErroConsultaCNPJ(Exception):
    pass


def so_digitos(cnpj: str) -> str:
    return re.sub(r"\D", "", str(cnpj or ""))


def cnpj_valido(cnpj: str) -> bool:
    """Dígitos verificadores do CNPJ (módulo 11). Ex.: 11.222.333/0001-81 é válido."""
    d = so_digitos(cnpj)
    if len(d) != 14 or d == d[0] * 14:
        return False
    for tamanho in (12, 13):
        pesos = list(range(tamanho - 7, 1, -1)) + list(range(9, 1, -1))
        soma = sum(int(n) * p for n, p in zip(d[:tamanho], pesos))
        dv = 11 - soma % 11
        if (0 if dv >= 10 else dv) != int(d[tamanho]):
            return False
    return True


def formatar_cnpj(cnpj: str) -> str:
    d = so_digitos(cnpj)
    return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:]}" if len(d) == 14 else str(cnpj)


@dataclass
class SocioQSA:
    nome: str
    qualificacao: str = ""
    pessoa_fisica: bool = True
    desde: str = ""


@dataclass
class DadosCNPJ:
    cnpj: str
    razao_social: str
    nome_fantasia: str = ""
    situacao: str = ""
    abertura: str = ""
    natureza_juridica: str = ""
    porte: str = ""
    capital_social: float | None = None
    cnae_principal: str = ""
    cnae_descricao: str = ""
    cnaes_secundarios: list[str] = field(default_factory=list)
    municipio: str = ""
    uf: str = ""
    endereco: str = ""
    simples: bool | None = None
    data_opcao_simples: str = ""
    mei: bool | None = None
    ultima_tributacao: str = ""          # ex.: "LUCRO PRESUMIDO (2024)"
    socios: list[SocioQSA] = field(default_factory=list)
    fonte: str = ""
    consultado_em: str = ""

    @property
    def ativa(self) -> bool:
        return self.situacao.upper().startswith("ATIVA")

    @property
    def atividade(self) -> str:
        return f"{self.cnae_principal} — {self.cnae_descricao}" if self.cnae_principal else self.cnae_descricao

    def regime_sugerido(self) -> str | None:
        """simples | presumido | real pelo cadastro público (None se não der para dizer)."""
        if self.simples:
            return "simples"
        forma = self.ultima_tributacao.split(" (")[0].upper()
        return FORMA_PARA_REGIME.get(forma)

    def como_dict(self) -> dict:
        return asdict(self)


def _cnae(codigo) -> str:
    d = so_digitos(codigo)
    return f"{d[:4]}-{d[4]}/{d[5:]}" if len(d) == 7 else str(codigo or "")


def _sim_nao(v) -> bool | None:
    if isinstance(v, bool) or v is None:
        return v
    return str(v).strip().lower() in ("sim", "s", "true", "1")


def de_brasilapi(j: dict) -> DadosCNPJ:
    regimes = sorted(j.get("regime_tributario") or [], key=lambda r: r.get("ano") or 0)
    ultima = f"{regimes[-1]['forma_de_tributacao']} ({regimes[-1]['ano']})" if regimes else ""
    endereco = " ".join(str(x) for x in (j.get("descricao_tipo_de_logradouro"), j.get("logradouro"),
                                         j.get("numero"), j.get("bairro"), j.get("cep")) if x)
    return DadosCNPJ(
        cnpj=formatar_cnpj(j.get("cnpj", "")), razao_social=j.get("razao_social") or "",
        nome_fantasia=j.get("nome_fantasia") or "", situacao=j.get("descricao_situacao_cadastral") or "",
        abertura=j.get("data_inicio_atividade") or "", natureza_juridica=j.get("natureza_juridica") or "",
        porte=j.get("porte") or "", capital_social=j.get("capital_social"),
        cnae_principal=_cnae(j.get("cnae_fiscal")), cnae_descricao=j.get("cnae_fiscal_descricao") or "",
        cnaes_secundarios=[f"{_cnae(c.get('codigo'))} — {c.get('descricao', '')}" for c in j.get("cnaes_secundarios") or []
                           if c.get("codigo")],
        municipio=(j.get("municipio") or "").title(), uf=j.get("uf") or "", endereco=endereco,
        simples=_sim_nao(j.get("opcao_pelo_simples")), data_opcao_simples=j.get("data_opcao_pelo_simples") or "",
        mei=_sim_nao(j.get("opcao_pelo_mei")), ultima_tributacao=ultima,
        socios=[SocioQSA(s.get("nome_socio") or "", s.get("qualificacao_socio") or "",
                         s.get("identificador_de_socio") == 2, s.get("data_entrada_sociedade") or "")
                for s in j.get("qsa") or []],
        fonte="BrasilAPI (dados abertos da Receita Federal)")


def de_cnpjws(j: dict) -> DadosCNPJ:
    e = j.get("estabelecimento") or {}
    simples = j.get("simples") or {}
    principal = e.get("atividade_principal") or {}
    cap = j.get("capital_social")
    endereco = " ".join(str(x) for x in (e.get("tipo_logradouro"), e.get("logradouro"), e.get("numero"),
                                         e.get("bairro"), e.get("cep")) if x)
    return DadosCNPJ(
        cnpj=formatar_cnpj(e.get("cnpj") or j.get("cnpj_raiz", "")), razao_social=j.get("razao_social") or "",
        nome_fantasia=e.get("nome_fantasia") or "", situacao=(e.get("situacao_cadastral") or "").upper(),
        abertura=e.get("data_inicio_atividade") or "", natureza_juridica=(j.get("natureza_juridica") or {}).get("descricao", ""),
        porte=(j.get("porte") or {}).get("descricao", ""), capital_social=float(cap) if cap else None,
        cnae_principal=_cnae(principal.get("id")), cnae_descricao=principal.get("descricao", ""),
        cnaes_secundarios=[f"{_cnae(a.get('id'))} — {a.get('descricao', '')}" for a in e.get("atividades_secundarias") or []],
        municipio=(e.get("cidade") or {}).get("nome", ""), uf=(e.get("estado") or {}).get("sigla", ""), endereco=endereco,
        simples=_sim_nao(simples.get("simples")) if simples else None,
        data_opcao_simples=simples.get("data_opcao_simples") or "",
        mei=_sim_nao(simples.get("mei")) if simples else None,
        socios=[SocioQSA(s.get("nome") or "", ((s.get("qualificacao_socio") or {}).get("descricao") or "").strip(),
                         "sica" in (s.get("tipo") or "").lower(), s.get("data_entrada") or "")
                for s in j.get("socios") or []],
        fonte="CNPJ.ws (dados abertos da Receita Federal)")


def _baixar(url: str, timeout: float) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "ZeraPlanejamento/1.0", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def consultar_cnpj(cnpj: str, timeout: float = 15.0) -> DadosCNPJ:
    """Consulta o CNPJ (BrasilAPI e, se falhar, CNPJ.ws). Levanta ``ErroConsultaCNPJ`` com mensagem clara."""
    d = so_digitos(cnpj)
    if not cnpj_valido(d):
        raise ErroConsultaCNPJ("CNPJ inválido: confira os 14 dígitos.")
    erros = []
    for fonte, conversor in (("brasilapi", de_brasilapi), ("cnpjws", de_cnpjws)):
        try:
            dados = conversor(_baixar(URL[fonte].format(d), timeout))
            if not dados.razao_social:
                raise ErroConsultaCNPJ("resposta sem razão social")
            dados.consultado_em = f"{dt.datetime.now():%d/%m/%Y %H:%M}"
            return dados
        except urllib.error.HTTPError as erro:
            if erro.code == 404:
                raise ErroConsultaCNPJ("CNPJ não encontrado na base da Receita Federal.") from erro
            erros.append(f"{fonte}: HTTP {erro.code}")
        except (urllib.error.URLError, TimeoutError, OSError, ValueError, ErroConsultaCNPJ) as erro:
            erros.append(f"{fonte}: {getattr(erro, 'reason', erro)}")
    raise ErroConsultaCNPJ("Não foi possível consultar agora (" + "; ".join(erros) + "). Verifique a internet ou "
                           "preencha manualmente.")
