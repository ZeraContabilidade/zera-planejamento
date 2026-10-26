"""
Cadastro do cliente e pastas de dados.

Cada cliente tem uma pasta em ``<dados>/clientes/<cnpj8>_<nome>/`` com:

- ``cliente.json``          premissas (este módulo)
- ``base_mensal.csv``       base mensal consolidada (``base.py``)
- ``base_origem.csv``       de onde veio cada valor
- ``importacoes/<data>/``   relatórios originais e conferência de cada importação
- ``relatorios/``           Excel e PDF gerados

A pasta ``<dados>`` vem da variável ``ZERA_DADOS``; sem ela, ``C:\\ZeraPlanejamento\\dados``
no Windows e ``~/ZeraPlanejamento/dados`` nos demais sistemas.
"""
from __future__ import annotations

import json
import os
import platform
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

from .formatos import slug
from .regras.federais import PRESUNCAO_PADRAO, RegrasFederais
from .regras.reforma import RegrasReforma

ANEXO_SERVICO = {"III": "rec_anexo_iii", "IV": "rec_anexo_iv", "V": "rec_anexo_v", "fator_r": "rec_fator_r"}


def pasta_dados() -> Path:
    if os.environ.get("ZERA_DADOS"):
        p = Path(os.environ["ZERA_DADOS"])
    elif platform.system() == "Windows":
        p = Path(r"C:\ZeraPlanejamento\dados")
    else:
        p = Path.home() / "ZeraPlanejamento" / "dados"
    (p / "clientes").mkdir(parents=True, exist_ok=True)
    return p


@dataclass
class Projecao:
    meses: int = 6
    janela: int = 12
    metodo: str = "tendencia"          # "tendencia" | "media"
    otimista: float = 0.15
    pessimista: float = -0.15
    sazonalidade: str = "auto"         # "auto" | "sim" | "nao"


@dataclass
class Socio:
    """Sócio pessoa física (visão sócio + empresa da Lei 15.270/2025 e otimizador de pró-labore)."""
    nome: str
    participacao: float = 1.0                 # fração do lucro distribuído (0–1)
    pro_labore: float | None = None           # mensal; vazio = pró-labore da base × participação
    dependentes: int = 0
    outros_rendimentos: float = 0.0           # renda anual de outras fontes (entra na base do IRPFM)


@dataclass
class Cliente:
    nome: str
    cnpj: str = ""
    municipio: str = ""
    uf: str = "SP"
    atividade: str = ""
    regime_atual: str = "simples"      # simples | presumido | real
    anexo_servico: str = "III"         # III | IV | V | fator_r  (destino das notas de serviço)
    iss_aliquota: float = 0.05         # do município/código de serviço
    icms_aliquota_saida: float = 0.18  # estimativa quando o cliente está no Simples
    icms_aliquota_entrada: float = 0.12
    rat: float = 0.02
    fap: float = 1.0
    terceiros: float = 0.058
    fator_r_incluir_cpp: bool = False
    lr_periodo: str = "trimestral"     # trimestral | anual
    prejuizo_fiscal_inicial: float = 0.0
    base_negativa_inicial: float = 0.0
    lucro_anual_estimado: float | None = None   # usado só se não houver custos/despesas
    presuncao: dict[str, list[float]] = field(default_factory=dict)   # sobrescreve PRESUNCAO_PADRAO
    reforma: dict[str, float] = field(default_factory=dict)           # cbs_referencia, ibs_referencia
    projecao: Projecao = field(default_factory=Projecao)
    depara: list[dict] = field(default_factory=list)                  # regras próprias do cliente
    socios: list[Socio] = field(default_factory=list)
    distribuicao_lucro: float = 1.0    # fração do lucro contábil distribuída aos sócios
    distribuicao_forma: str = "mensal"  # mensal | anual (um pagamento no fim do período)
    cnae: str = ""                      # CNAE principal (consulta à Receita)
    dados_receita: dict = field(default_factory=dict)   # última consulta do CNPJ (dados abertos da RFB)
    mapa_rotulos: dict[str, str] = field(default_factory=dict)   # rótulo de documento → coluna da base (importação livre)
    observacoes: str = ""

    # ---------------- caminhos ----------------
    @property
    def id(self) -> str:
        raiz = "".join(ch for ch in self.cnpj if ch.isdigit())[:8] or "semcnpj"
        return f"{raiz}_{slug(self.nome)[:40]}"

    def pasta(self, dados: Path | None = None) -> Path:
        p = (dados or pasta_dados()) / "clientes" / self.id
        for sub in ("importacoes", "relatorios"):
            (p / sub).mkdir(parents=True, exist_ok=True)
        return p

    # ---------------- regras efetivas ----------------
    def regras_federais(self) -> RegrasFederais:
        r = RegrasFederais()
        pres = dict(PRESUNCAO_PADRAO)
        for col, (irpj, csll) in self.presuncao.items():
            pres[col] = (float(irpj), float(csll))
        r.presuncao = pres
        return r

    def regras_reforma(self) -> RegrasReforma:
        r = RegrasReforma()
        for k in ("cbs_referencia", "ibs_referencia", "reducao_aliquota"):
            if k in self.reforma:
                setattr(r, k, float(self.reforma[k]))
        return r

    @property
    def coluna_servico(self) -> str:
        return ANEXO_SERVICO.get(self.anexo_servico, "rec_anexo_iii")

    # ---------------- persistência ----------------
    def salvar(self, dados: Path | None = None) -> Path:
        caminho = self.pasta(dados) / "cliente.json"
        caminho.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8")
        return caminho

    @classmethod
    def de_dict(cls, d: dict) -> "Cliente":
        validos = {f.name for f in fields(cls)}
        d = {k: v for k, v in d.items() if k in validos}
        if isinstance(d.get("projecao"), dict):
            d["projecao"] = Projecao(**{k: v for k, v in d["projecao"].items()
                                        if k in {f.name for f in fields(Projecao)}})
        if d.get("socios"):
            validos_s = {f.name for f in fields(Socio)}
            d["socios"] = [s if isinstance(s, Socio) else Socio(**{k: v for k, v in s.items() if k in validos_s})
                           for s in d["socios"]]
        return cls(**d)

    @classmethod
    def carregar(cls, caminho: Path) -> "Cliente":
        return cls.de_dict(json.loads(Path(caminho).read_text(encoding="utf-8")))


def listar_clientes(dados: Path | None = None) -> list[Cliente]:
    raiz = (dados or pasta_dados()) / "clientes"
    saida = []
    for p in sorted(raiz.glob("*/cliente.json")):
        try:
            saida.append(Cliente.carregar(p))
        except Exception:  # noqa: BLE001 — cadastro corrompido não derruba a lista
            continue
    return saida
