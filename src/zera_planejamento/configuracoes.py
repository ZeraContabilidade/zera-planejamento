"""
Configurações do escritório (valem para todos os clientes), em ``<dados>/configuracoes.json``.

kit_identidade   pasta "ZERA - IDENTIDADE VISUAL" (header_a4.png, logo_zera.png, fonts/)
responsavel      assinatura dos relatórios
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, fields
from pathlib import Path

from .cliente import pasta_dados

CANDIDATOS_KIT = [
    Path(r"G:\Meu Drive\ZERA - IDENTIDADE VISUAL"),
    Path.home() / "Meu Drive" / "ZERA - IDENTIDADE VISUAL",
    Path(r"C:\ZeraPlanejamento\ZERA - IDENTIDADE VISUAL"),
]


@dataclass
class Configuracoes:
    kit_identidade: str = ""
    responsavel: str = "Equipe Zera Contabilidade"
    escritorio: str = "ZERA ASSESSORIA EMPRESARIAL E CONTÁBIL"

    @classmethod
    def carregar(cls, dados: Path | None = None) -> "Configuracoes":
        arq = (dados or pasta_dados()) / "configuracoes.json"
        cfg = cls()
        if arq.exists():
            d = json.loads(arq.read_text(encoding="utf-8"))
            cfg = cls(**{k: v for k, v in d.items() if k in {f.name for f in fields(cls)}})
        if not cfg.kit_identidade:
            for c in CANDIDATOS_KIT:
                if c.exists():
                    cfg.kit_identidade = str(c)
                    break
        return cfg

    def salvar(self, dados: Path | None = None) -> None:
        arq = (dados or pasta_dados()) / "configuracoes.json"
        arq.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8")

    @property
    def kit(self) -> Path | None:
        p = Path(self.kit_identidade) if self.kit_identidade else None
        return p if p and p.exists() else None
