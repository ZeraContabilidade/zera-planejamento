"""Saídas: gráficos (PNG), Excel com gráficos nativos e PDF com a identidade da Zera."""
from __future__ import annotations

from pathlib import Path

from ..formatos import slug
from . import graficos
from .excel import exportar_excel
from .pdf import exportar_pdf


def gerar_relatorios(pl, pasta: Path) -> dict[str, Path]:
    """Gera PNG, XLSX e PDF numa subpasta datada; devolve os caminhos."""
    destino = pasta / f"{pl.gerado_em:%Y%m%d-%H%M}"
    destino.mkdir(parents=True, exist_ok=True)
    png = graficos.gerar(pl, destino)
    nome = f"Planejamento_Tributario_{slug(pl.cliente.nome)[:40]}"
    xlsx = exportar_excel(pl, destino / f"{nome}.xlsx", png)
    pdf = exportar_pdf(pl, destino / f"{nome}.pdf", png)
    return {**png, "excel": xlsx, "pdf": pdf}


__all__ = ["gerar_relatorios", "exportar_excel", "exportar_pdf", "graficos"]
