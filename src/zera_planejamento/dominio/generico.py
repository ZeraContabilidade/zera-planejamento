"""
Importação livre: qualquer planilha (.xlsx, .xlsm, .xls, .ods, .csv) ou PDF com texto vira valores mensais da base.

Não presume layout. O fluxo é:

1. ``ler_tabelas``: todas as abas da planilha, ou as tabelas de cada página do PDF (se a página não tiver tabela
   desenhada, as linhas de texto são quebradas em colunas por espaços largos). PDF digitalizado (só imagem) não
   tem texto: o sistema avisa e pede o arquivo original.
2. ``detectar_layout``: procura os meses — numa linha de cabeçalho (jan/26, 01/2026, 2026-01, datas...) com os
   valores nas colunas, ou numa coluna de datas com os valores nas linhas. Sem meses, o documento é de um único
   período e o usuário informa a competência.
3. ``extrair``: devolve uma tabela longa (rótulo, competência, valor).
4. O usuário liga cada rótulo a uma coluna da base (ou "ignorar"). O mapa fica salvo no cadastro do cliente
   (``Cliente.mapa_rotulos``) e é reaplicado sozinho nos próximos documentos com os mesmos rótulos.
5. ``montar_parcial``: soma por mês e coluna (valores em módulo; a base guarda receitas, custos e despesas
   positivos). Valores acumulados no ano viram mensais pela diferença entre meses.
"""
from __future__ import annotations

import csv
import datetime as dt
import io
import re
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from ..base import COLUNAS
from .leitura import normalizar, numero

EXTENSOES = (".xlsx", ".xlsm", ".xls", ".ods", ".csv", ".pdf")
IGNORAR = "ignorar"
MESES = {"jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6, "jul": 7, "ago": 8, "set": 9, "out": 10,
         "nov": 11, "dez": 12, "feb": 2, "apr": 4, "may": 5, "aug": 8, "sep": 9, "oct": 10, "dec": 12}
_RE_MES_ANO = re.compile(r"^([a-z]{3})[a-z]*\.?[\s/\-.]*(\d{2}|\d{4})$")
_RE_NUM_MES_ANO = re.compile(r"^(\d{1,2})[/\-.](\d{4})$")
_RE_ANO_MES = re.compile(r"^(\d{4})[/\-.](\d{1,2})$")
_RE_DATA = re.compile(r"^(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})$")
_RE_ISO = re.compile(r"^(\d{4})-(\d{2})-(\d{2})")

# Sugestões iniciais de destino pelo rótulo (o usuário confirma na tela). Ordem importa: a primeira que casar vale.
SUGESTOES: list[tuple[str, str]] = [
    (r"^(total|subtotal|soma|lucro|prejuizo|resultado|saldo|margem)", IGNORAR),
    (r"devoluc|cancelad", "devolucoes"),
    (r"receitas? financeir|rendimentos? de aplic|juros (ativos|recebidos)|descontos obtidos", "receitas_financeiras"),
    (r"pro[- ]?labore|retirada.*socio", "pro_labore"),
    (r"fgts", "fgts"),
    (r"salario|ordenado|folha de pagamento|remuneracao|ferias|13", "salarios"),
    (r"energia eletrica|luz", "cred_energia"),
    (r"frete", "cred_fretes"),
    (r"custo|cmv|csp|mercadorias vendidas|servicos prestados.*custo", "custos"),
    (r"vendas? de mercadoria|revenda", "rec_anexo_i"),
    (r"industrializ|produtos? (vendidos|fabricados)", "rec_anexo_ii"),
    (r"receita|faturamento|servicos? prestados|vendas", "@servico"),    # coluna de serviço do cadastro
    (r"despesa|aluguel|honorario|telefone|internet|material|manutencao|seguro|tarifa", "despesas"),
]


class ErroLeituraDocumento(Exception):
    pass


@dataclass
class Tabela:
    origem: str                     # "Aba Plan1", "Página 2 · tabela 1", "Página 3 · texto"
    linhas: list[list]

    @property
    def tamanho(self) -> str:
        return f"{len(self.linhas)} linhas × {max((len(l) for l in self.linhas), default=0)} colunas"


@dataclass
class Layout:
    tipo: str                                   # "colunas" | "linhas" | "unico"
    linha_cabecalho: int | None = None          # colunas: linha com os meses
    meses_por_coluna: dict[int, pd.Period] = field(default_factory=dict)
    coluna_rotulo: int | None = None
    coluna_data: int | None = None              # linhas: coluna com a competência
    colunas_valor: list[int] = field(default_factory=list)

    def descricao(self) -> str:
        if self.tipo == "colunas":
            m = sorted(self.meses_por_coluna.values())
            return f"{len(m)} meses nas colunas ({_comp(m[0])} a {_comp(m[-1])})"
        if self.tipo == "linhas":
            return "competência numa coluna de datas, valores nas linhas"
        return "sem meses: documento de um período (informe a competência)"


def _comp(p: pd.Period) -> str:
    return f"{['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez'][p.month - 1]}/{str(p.year)[2:]}"


# ---------------------------------------------------------------------------------------------------- leitura
def _limpar(linhas: list[list]) -> list[list]:
    saida = []
    for linha in linhas:
        cel = [None if (c is None or (isinstance(c, str) and not c.strip())) else c for c in linha]
        while cel and cel[-1] is None:
            cel.pop()
        if any(c is not None for c in cel):
            saida.append(cel)
    return saida


def _ler_planilha(caminho: Path) -> list[Tabela]:
    from python_calamine import CalamineWorkbook
    try:
        wb = CalamineWorkbook.from_path(str(caminho))
    except Exception as erro:  # noqa: BLE001 — repassa com mensagem clara
        raise ErroLeituraDocumento(f"Não consegui abrir a planilha: {erro}") from erro
    tabelas = []
    for nome in wb.sheet_names:
        linhas = _limpar(wb.get_sheet_by_name(nome).to_python())
        if linhas:
            tabelas.append(Tabela(f"Aba {nome}", linhas))
    return tabelas


def _ler_csv(caminho: Path) -> list[Tabela]:
    bruto = caminho.read_bytes()
    for codificacao in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            texto = bruto.decode(codificacao)
            break
        except UnicodeDecodeError:
            continue
    try:
        dialeto = csv.Sniffer().sniff(texto[:4000], delimiters=";,\t|")
    except csv.Error:
        dialeto = csv.excel
        dialeto.delimiter = ";"
    return [Tabela("CSV", _limpar([list(l) for l in csv.reader(io.StringIO(texto), dialeto)]))]


def _celula_de_valor(token: str) -> bool:
    return token in ("-", "–") or competencia(token) is not None or _valor(token) is not None


def _texto_em_colunas(texto: str) -> list[list]:
    """Linhas de texto do PDF em colunas: da direita para a esquerda, números e meses viram colunas e o que
    sobra à esquerda é o rótulo. Ex.: "Salários e ordenados 15.000,00 (1.200,00)" → [rótulo, valor, valor]."""
    linhas = []
    for linha in texto.splitlines():
        tokens = linha.split()
        if not tokens:
            continue
        fim = len(tokens)
        while fim > 0 and _celula_de_valor(tokens[fim - 1]):
            fim -= 1
        rotulo = " ".join(tokens[:fim])
        valores = [None if t in ("-", "–") else t for t in tokens[fim:]]
        linhas.append(([rotulo] if rotulo else [None]) + valores)
    return linhas


def _ler_pdf(caminho: Path) -> list[Tabela]:
    import pdfplumber
    tabelas, com_texto = [], False
    try:
        pdf = pdfplumber.open(str(caminho))
    except Exception as erro:  # noqa: BLE001
        raise ErroLeituraDocumento(f"Não consegui abrir o PDF: {erro}") from erro
    with pdf:
        for n, pagina in enumerate(pdf.pages, start=1):
            texto = pagina.extract_text() or ""
            com_texto |= bool(texto.strip())
            achadas = [t for t in (pagina.extract_tables() or []) if t and len(t) > 1]
            for i, t in enumerate(achadas, start=1):
                tabelas.append(Tabela(f"Página {n} · tabela {i}", _limpar(t)))
            if not achadas and texto.strip():
                tabelas.append(Tabela(f"Página {n} · texto", _limpar(_texto_em_colunas(texto))))
    if not com_texto:
        raise ErroLeituraDocumento("PDF sem texto (digitalizado como imagem). Peça o arquivo original, exportado do "
                                   "sistema, ou a versão em Excel.")
    return [t for t in tabelas if t.linhas]


def ler_tabelas(caminho: str | Path) -> list[Tabela]:
    """Todas as tabelas de um documento (abas da planilha ou páginas do PDF)."""
    caminho = Path(caminho)
    ext = caminho.suffix.lower()
    if ext not in EXTENSOES:
        raise ErroLeituraDocumento(f"Formato {ext or 'sem extensão'} não suportado. Use Excel, CSV ou PDF.")
    if ext == ".pdf":
        tabelas = _ler_pdf(caminho)
    elif ext == ".csv":
        tabelas = _ler_csv(caminho)
    else:
        tabelas = _ler_planilha(caminho)
    if not tabelas:
        raise ErroLeituraDocumento("O documento não tem tabelas nem linhas com conteúdo.")
    return tabelas


# ---------------------------------------------------------------------------------------------------- meses
def competencia(valor) -> pd.Period | None:
    """Competência de uma célula: datas, "jan/26", "janeiro 2026", "01/2026", "2026-01", "31/01/2026"..."""
    if valor is None or isinstance(valor, bool):
        return None
    if isinstance(valor, (dt.datetime, dt.date, pd.Timestamp)):
        return pd.Period(year=valor.year, month=valor.month, freq="M")
    if isinstance(valor, (int, float)):
        return None
    t = normalizar(valor).replace("º", "")
    t = re.sub(r"^(competencia|mes|periodo)\s*:?\s*", "", t)
    if m := _RE_MES_ANO.match(t):
        mes = MESES.get(m.group(1))
        if mes:
            ano = int(m.group(2))
            return pd.Period(year=ano + 2000 if ano < 100 else ano, month=mes, freq="M")
    if m := _RE_NUM_MES_ANO.match(t):
        if 1 <= int(m.group(1)) <= 12:
            return pd.Period(year=int(m.group(2)), month=int(m.group(1)), freq="M")
    if m := _RE_ANO_MES.match(t):
        if 1 <= int(m.group(2)) <= 12:
            return pd.Period(year=int(m.group(1)), month=int(m.group(2)), freq="M")
    if m := _RE_DATA.match(t):
        dia, mes, ano = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 1 <= mes <= 12 and 1 <= dia <= 31:
            return pd.Period(year=ano + 2000 if ano < 100 else ano, month=mes, freq="M")
    if m := _RE_ISO.match(t):
        return pd.Period(year=int(m.group(1)), month=int(m.group(2)), freq="M")
    return None


def _valor(c) -> float | None:
    if isinstance(c, bool):
        return None
    if isinstance(c, (int, float)):
        return float(c)
    if isinstance(c, str):
        t = c.strip()
        negativo = (t.startswith("(") and t.endswith(")")) or t.endswith("-") or t.endswith(" D")
        t = t.strip("()").rstrip("-").removesuffix(" D").removesuffix(" C").replace("R$", "").strip()
        v = numero(t)
        if v is not None:
            return -abs(v) if negativo else v
    return None


def _texto(c) -> bool:
    return isinstance(c, str) and _valor(c) is None and competencia(c) is None and bool(re.search(r"[A-Za-zÀ-ú]", c))


def detectar_layout(tab: Tabela) -> Layout:
    linhas = tab.linhas
    # 1) cabeçalho com meses nas colunas
    melhor = None
    for i, linha in enumerate(linhas[:40]):
        meses = {j: p for j, c in enumerate(linha) if (p := competencia(c)) is not None}
        if len(meses) >= 2 and len(set(meses.values())) == len(meses) and (melhor is None or len(meses) > len(melhor[1])):
            melhor = (i, meses)
    if melhor:
        i, meses = melhor
        primeira = min(meses)
        candidatas = range(0, primeira) if primeira > 0 else [c for c in range(len(linhas[i])) if c not in meses]
        rot = max(candidatas, key=lambda j: sum(_texto(l[j]) for l in linhas[i + 1:] if j < len(l)), default=None)
        return Layout("colunas", linha_cabecalho=i, meses_por_coluna=meses, coluna_rotulo=rot)
    # 2) coluna de datas com valores nas linhas
    largura = max(len(l) for l in linhas)
    for j in range(largura):
        n = sum(competencia(l[j]) is not None for l in linhas if j < len(l))
        if n >= 2:
            valores = [k for k in range(largura) if k != j and
                       sum(_valor(l[k]) is not None for l in linhas if k < len(l) and competencia(l[j]) is not None) >= 2]
            if valores:
                return Layout("linhas", coluna_data=j, colunas_valor=valores)
    # 3) um período só: rótulo + valor
    rot = max(range(largura), key=lambda j: sum(_texto(l[j]) for l in linhas if j < len(l)))
    numericas = [k for k in range(largura) if k != rot and sum(_valor(l[k]) is not None for l in linhas if k < len(l)) >= 2]
    return Layout("unico", coluna_rotulo=rot, colunas_valor=numericas[-1:] if numericas else [])


def _cabecalho_coluna(tab: Tabela, j: int, ate: int) -> str:
    for linha in tab.linhas[:ate]:
        if j < len(linha) and _texto(linha[j]):
            return str(linha[j]).strip()
    return f"Coluna {j + 1}"


def extrair(tab: Tabela, layout: Layout, competencia_unica: pd.Period | None = None) -> pd.DataFrame:
    """Tabela longa: rotulo, competencia, valor (sinal original)."""
    reg = []
    if layout.tipo == "colunas":
        for linha in tab.linhas[layout.linha_cabecalho + 1:]:
            rotulo = linha[layout.coluna_rotulo] if layout.coluna_rotulo is not None and layout.coluna_rotulo < len(linha) else None
            if not _texto(rotulo):
                continue
            for j, per in layout.meses_por_coluna.items():
                v = _valor(linha[j]) if j < len(linha) else None
                if v is not None:
                    reg.append((str(rotulo).strip(), per, v))
    elif layout.tipo == "linhas":
        primeira_data = min((i for i, l in enumerate(tab.linhas) if layout.coluna_data < len(l)
                             and competencia(l[layout.coluna_data]) is not None), default=0)
        nomes = {k: _cabecalho_coluna(tab, k, primeira_data) for k in layout.colunas_valor}
        for linha in tab.linhas:
            per = competencia(linha[layout.coluna_data]) if layout.coluna_data < len(linha) else None
            if per is None:
                continue
            for k in layout.colunas_valor:
                v = _valor(linha[k]) if k < len(linha) else None
                if v is not None:
                    reg.append((nomes[k], per, v))
    else:
        if competencia_unica is None or not layout.colunas_valor:
            return pd.DataFrame(columns=["rotulo", "competencia", "valor"])
        k = layout.colunas_valor[0]
        for linha in tab.linhas:
            rotulo = linha[layout.coluna_rotulo] if layout.coluna_rotulo < len(linha) else None
            v = _valor(linha[k]) if k < len(linha) else None
            if _texto(rotulo) and v is not None:
                reg.append((str(rotulo).strip(), competencia_unica, v))
    return pd.DataFrame(reg, columns=["rotulo", "competencia", "valor"])


# ---------------------------------------------------------------------------------------------------- destino
def sugerir_destino(rotulo: str, coluna_servico: str = "rec_anexo_iii") -> str:
    t = normalizar(rotulo)
    for padrao, destino in SUGESTOES:
        if re.search(padrao, t):
            return coluna_servico if destino == "@servico" else destino
    return IGNORAR


def destinos(mapa: dict[str, str], rotulos, coluna_servico: str) -> dict[str, tuple[str, str]]:
    """Para cada rótulo: (destino, origem da escolha: "salvo" no cliente ou "sugerido")."""
    saida = {}
    for r in rotulos:
        chave = normalizar(r)
        saida[r] = (mapa[chave], "salvo") if chave in mapa else (sugerir_destino(r, coluna_servico), "sugerido")
    return saida


def montar_parcial(longo: pd.DataFrame, destino_por_rotulo: dict[str, str], acumulado: bool = False) -> pd.DataFrame:
    """Valores mensais por coluna da base (soma dos rótulos ligados à mesma coluna; valores em módulo)."""
    if longo.empty:
        return pd.DataFrame(columns=list(COLUNAS))
    d = longo.copy()
    d["destino"] = d["rotulo"].map(destino_por_rotulo).fillna(IGNORAR)
    d = d[d["destino"].isin(COLUNAS)]
    if d.empty:
        return pd.DataFrame(columns=list(COLUNAS))
    d = d.groupby(["rotulo", "destino", "competencia"], as_index=False)["valor"].sum()
    if acumulado:     # acumulado no ano → mensal: mês − mês anterior do mesmo ano (janeiro fica como está)
        d = d.sort_values("competencia")
        d["ano"] = d["competencia"].map(lambda p: p.year)
        d["valor"] = d.groupby(["rotulo", "ano"])["valor"].diff().fillna(d["valor"])
    d["valor"] = d["valor"].abs()
    parcial = d.pivot_table(index="competencia", columns="destino", values="valor", aggfunc="sum")
    parcial.index = pd.PeriodIndex(parcial.index, freq="M", name="competencia")
    return parcial.sort_index()


def lembrar(mapa: dict[str, str], destino_por_rotulo: dict[str, str]) -> dict[str, str]:
    """Atualiza o mapa do cliente com as escolhas desta importação."""
    novo = dict(mapa)
    for rotulo, destino in destino_por_rotulo.items():
        novo[normalizar(rotulo)] = destino
    return novo
