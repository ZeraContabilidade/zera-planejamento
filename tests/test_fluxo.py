"""Base, projeção, equilíbrio, relatórios, linha de comando e app — fluxo completo com dados sintéticos."""
import math

import openpyxl
import pandas as pd
import pytest

from zera_planejamento.base import BaseMensal
from zera_planejamento.planejamento import gerar_planejamento
from zera_planejamento.projecao import projetar


def test_base_salvar_carregar(tmp_path, base_exemplo):
    base_exemplo.dados.loc["2026-01", "cred_aluguel"] = 1234.56
    base_exemplo.salvar(tmp_path)
    b = BaseMensal.carregar(tmp_path)
    assert b.dados.loc["2026-01", "cred_aluguel"] == 1234.56
    assert b.origem.loc["2025-05", "rec_anexo_iii"] == "exemplo"
    assert len(b.meses) == len(base_exemplo.meses)


def test_planilha_de_digitacao(tmp_path, base_exemplo):
    arq = base_exemplo.para_planilha(tmp_path / "base.xlsx")
    df = BaseMensal.de_planilha(arq)
    assert math.isclose(df.loc["2026-09", "rec_anexo_iii"], base_exemplo.dados.loc["2026-09", "rec_anexo_iii"])


def test_projecao_cenarios(base_exemplo, cliente):
    cen = projetar(base_exemplo, cliente)
    n, o, p = cen["Neutro"], cen["Otimista"], cen["Pessimista"]
    assert list(n.meses.astype(str)) == ["2026-10", "2026-11", "2026-12", "2027-01", "2027-02", "2027-03"]
    rn = n.base_projetada.receita_bruta().sum()
    assert math.isclose(o.base_projetada.receita_bruta().sum(), rn * 1.15)
    assert math.isclose(p.base_projetada.receita_bruta().sum(), rn * 0.85)
    # tendência linear de +2.000/mês continua: out/26 = 80.000 + 2.000 × 21
    assert math.isclose(n.base_projetada.dados.loc["2026-10", "rec_anexo_iii"], 122_000, rel_tol=1e-9)
    # folha é fixa (média dos últimos 3 meses) e não muda com o cenário
    assert (o.base_projetada.dados["salarios"] == 15_000).all()


def test_planejamento_completo(base_exemplo, cliente):
    pl = gerar_planejamento(cliente, base_exemplo)
    assert set(pl.resumo.cenario) == {"Neutro", "Otimista", "Pessimista"}
    assert pl.resumo.groupby("cenario").melhor.sum().eq(1).all()
    assert {"Lucro Real × Lucro Presumido", "Simples × Lucro Presumido"} <= set(pl.equilibrio.comparacao)
    assert list(pl.transicao.index) == list(range(2026, 2034))
    assert not pl.curva.empty


def test_relatorios(tmp_path, base_exemplo, cliente, monkeypatch):
    monkeypatch.setenv("ZERA_DADOS", str(tmp_path / "dados"))
    from zera_planejamento.cliente import Socio
    from zera_planejamento.relatorio import gerar_relatorios
    cliente.socios = [Socio("Sócio Um", 0.7), Socio("Sócio Dois", 0.3)]
    pl = gerar_planejamento(cliente, base_exemplo)
    arqs = gerar_relatorios(pl, tmp_path / "rel")
    assert arqs["pdf"].stat().st_size > 50_000
    wb = openpyxl.load_workbook(arqs["excel"])
    assert {"Resumo", "Histórico mensal", "Simples Nacional", "Lucro Presumido", "Lucro Real", "Base mensal",
            "Transição 2026-2033", "Sócios e empresa", "Prazos", "Premissas", "Alertas"} <= set(wb.sheetnames)
    assert wb["Resumo"]._charts and wb["Histórico mensal"]._charts


def test_cli(tmp_path, monkeypatch, relatorios, cliente, capsys):
    monkeypatch.setenv("ZERA_DADOS", str(tmp_path / "dados"))
    from zera_planejamento.cli import main
    cliente.salvar()
    assert main(["importar", "--cliente", "11222333", *map(str, relatorios.values())]) == 0
    assert main(["clientes"]) == 0
    assert "Empresa Teste" in capsys.readouterr().out


def test_app_todas_as_paginas(tmp_path, monkeypatch, base_exemplo, cliente):
    from streamlit.testing.v1 import AppTest
    monkeypatch.setenv("ZERA_DADOS", str(tmp_path / "dados"))
    from zera_planejamento.cliente import Socio
    cliente.socios = [Socio("Sócio Um", 1.0)]
    cliente.salvar()
    base_exemplo.salvar(cliente.pasta())
    import zera_planejamento.app as app_pkg
    from pathlib import Path
    main = Path(app_pkg.__file__).parent / "main.py"
    for pagina in ("cadastro", "importar", "base", "planejamento", "socios", "relatorios", "carteira", "depara",
                   "configuracoes"):
        at = AppTest.from_file(str(main), default_timeout=300)
        at.session_state["cliente_id"] = cliente.id
        at.run()
        at.switch_page(f"paginas/{pagina}.py").run()
        assert not at.exception, f"{pagina}: {[e.message for e in at.exception]}"
