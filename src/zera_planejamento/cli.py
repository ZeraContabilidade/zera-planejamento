"""
Linha de comando.

    zera-planejamento app                                  abre a tela no navegador
    zera-planejamento clientes                             lista os clientes cadastrados
    zera-planejamento importar --cliente ID arquivos...    importa relatórios do Domínio para a base
    zera-planejamento relatorio --cliente ID               calcula e gera Excel + PDF
    zera-planejamento carteira [--excel arquivo.xlsx]      painel: quem deveria mudar de regime
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from .cliente import listar_clientes, pasta_dados


def _cliente(cid: str):
    for c in listar_clientes():
        if c.id == cid or c.id.startswith(cid) or "".join(ch for ch in c.cnpj if ch.isdigit()).startswith(cid):
            return c
    raise SystemExit(f"Cliente '{cid}' não encontrado. Use 'zera-planejamento clientes'.")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="zera-planejamento", description="Planejamento tributário Zera")
    sub = ap.add_subparsers(dest="comando", required=True)
    pa = sub.add_parser("app", help="Abre a tela no navegador")
    pa.add_argument("--porta", type=int, default=8501)
    sub.add_parser("clientes", help="Lista os clientes")
    pi = sub.add_parser("importar", help="Importa relatórios do Domínio")
    pi.add_argument("--cliente", required=True)
    pi.add_argument("arquivos", nargs="+")
    pr = sub.add_parser("relatorio", help="Gera Excel e PDF")
    pr.add_argument("--cliente", required=True)
    pc = sub.add_parser("carteira", help="Painel da carteira: quem deveria mudar de regime")
    pc.add_argument("--excel", help="Salva o painel neste arquivo .xlsx")
    a = ap.parse_args(argv)

    if a.comando == "app":
        cred = Path.home() / ".streamlit" / "credentials.toml"
        if not cred.exists():   # evita a pergunta de e-mail do Streamlit na primeira execução
            cred.parent.mkdir(parents=True, exist_ok=True)
            cred.write_text('[general]\nemail = ""\n', encoding="utf-8")
        main_py = Path(__file__).parent / "app" / "main.py"
        return subprocess.call([sys.executable, "-m", "streamlit", "run", str(main_py), "--server.port", str(a.porta),
                                "--browser.gatherUsageStats", "false", "--theme.base", "light",
                                "--theme.primaryColor", "#A8843F", "--theme.textColor", "#1A1A1A",
                                "--client.toolbarMode", "minimal"])
    if a.comando == "clientes":
        print(f"Dados em {pasta_dados()}")
        for c in listar_clientes():
            print(f"  {c.id:45s} {c.nome}")
        return 0
    if a.comando == "carteira":
        from .carteira import analisar_carteira
        from .formatos import brl
        df = analisar_carteira(progresso=lambda i, n, nome: print(f"[{i}/{n}] {nome}", file=sys.stderr))
        if df.empty:
            print("Nenhum cliente cadastrado.")
            return 0
        for r in df.itertuples():
            economia = getattr(r, "economia_ano", float("nan"))
            extra = f" — economia estimada {brl(economia)}/ano" if economia == economia and r.situacao == "MUDAR" else ""
            print(f"{r.situacao:13s} {r.cliente[:45]:45s} {r.leitura}{extra}")
        if a.excel:
            df.to_excel(a.excel, index=False)
            print(f"Excel: {a.excel}")
        return 0
    c = _cliente(a.cliente)
    from .base import BaseMensal
    if a.comando == "importar":
        from .dominio import importar_relatorios
        base = BaseMensal.carregar(c.pasta())
        imp = importar_relatorios([Path(x) for x in a.arquivos], c, base)
        for al in imp.alertas.itens:
            print(f"[{al.nivel}] {al.origem}: {al.mensagem}")
        if imp.alertas.contagem()["CRÍTICO"]:
            print("Importação NÃO gravada: há alerta crítico.", file=sys.stderr)
            return 1
        print(f"{imp.aplicar(base)} valores gravados.")
        base.salvar(c.pasta())
        return 0
    if a.comando == "relatorio":
        from .planejamento import gerar_planejamento
        from .relatorio import gerar_relatorios
        pl = gerar_planejamento(c, BaseMensal.carregar(c.pasta()))
        arqs = gerar_relatorios(pl, c.pasta() / "relatorios")
        m = pl.melhor("Neutro")
        if m is not None:
            print(f"Menor carga (Neutro): {m['rotulo']} — R$ {m['tributos']:,.2f} ({m['carga']:.2%})")
        print(f"Excel: {arqs['excel']}\nPDF:   {arqs['pdf']}")
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
