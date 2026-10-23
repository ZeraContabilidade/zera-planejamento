"""
Leitores dos relatórios do Domínio usados no planejamento:

- Acompanhamento de Serviços (Escrita Fiscal)    -> notas de serviço prestado
- Acompanhamento de Saídas  (Escrita Fiscal)     -> notas de venda (CFOP 5/6/7)
- Acompanhamento de Entradas (Escrita Fiscal)    -> notas de compra (CFOP 1/2/3)
- Extrato Mensal da folha (Folha)                -> remuneração, base INSS e FGTS
- D.R.E. (Contabilidade)                         -> custos, despesas e receitas financeiras

Cada leitor localiza as colunas pelo texto do cabeçalho e ignora cabeçalhos
repetidos a cada página, subtotais ("Total CFOP", "Total Geral") e rodapés.
"""
from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from .leitura import data, datas_no_texto, ler_planilha, normalizar, numero, so_digitos, texto_codigo, texto_linha


@dataclass
class Relatorio:
    tipo: str
    arquivo: str
    empresa: str = ""
    cnpj: str = ""
    inicio: dt.date | None = None
    fim: dt.date | None = None
    dados: pd.DataFrame = field(default_factory=pd.DataFrame)
    extras: dict = field(default_factory=dict)

    @property
    def meses(self) -> list[pd.Period]:
        if not (self.inicio and self.fim):
            return []
        return list(pd.period_range(pd.Period(self.inicio, "M"), pd.Period(self.fim, "M"), freq="M"))


# --------------------------------------------------------------------------
# Identificação e cabeçalho
# --------------------------------------------------------------------------
TITULOS = [
    ("servicos", "acompanhamento de servicos"),
    ("entradas", "acompanhamento de entradas"),
    ("saidas", "acompanhamento de saidas"),
    ("folha", "extrato mensal"),
    ("dre", "demonstracao do resultado"),
]


def identificar(linhas: list[list]) -> str | None:
    topo = normalizar(" ".join(texto_linha(l) for l in linhas[:12]))
    for tipo, chave in TITULOS:
        if chave in topo:
            return tipo
    return None


def _proximo(valores: list, i: int):
    for v in valores[i + 1:]:
        if v not in (None, ""):
            return v
    return None


def _rotulos(linha: list) -> dict[str, object]:
    """{rótulo normalizado sem ':' : próximo valor não vazio} para cada célula 'Rótulo:'."""
    vals = [v for v in linha if v not in (None, "")]
    saida = {}
    for i, v in enumerate(vals):
        if isinstance(v, str) and v.strip().endswith(":"):
            saida[normalizar(v).rstrip(":").strip()] = _proximo(vals, i)
    return saida


def _cabecalho(linhas: list[list], rel: Relatorio) -> None:
    for linha in linhas[:10]:
        r = _rotulos(linha)
        for chave in ("cnpj", "c.n.p.j."):
            if chave in r and not rel.cnpj:
                rel.cnpj = so_digitos(r[chave])
        if "empresa" in r and not rel.empresa:
            rel.empresa = re.sub(r"^\d+\s*-\s*", "", str(r["empresa"])).strip()
        if "periodo" in r and not rel.inicio:
            d = datas_no_texto(r["periodo"])
            if len(d) >= 2:
                rel.inicio, rel.fim = d[0], d[1]
    if not rel.empresa:
        primeira = next((v for v in linhas[0] if isinstance(v, str) and v.strip()), "")
        rel.empresa = primeira.strip()


# --------------------------------------------------------------------------
# Notas fiscais (Serviços, Entradas, Saídas)
# --------------------------------------------------------------------------
COLUNAS_NOTA = {
    "data": "data", "nota": "nota", "serie": "serie", "especie": "especie",
    "cliente": "participante", "fornecedor": "participante", "cfop": "cfop", "ac.": "acumulador",
    "uf": "uf", "valor contabil": "valor", "tipo": "imposto", "base calculo": "base", "aliq.": "aliquota",
    "valor": "valor_imposto", "isentas": "isentas", "outras": "outras",
}


def _mapa_cabecalho(linha: list) -> dict[str, int] | None:
    rotulos = {i: normalizar(v) for i, v in enumerate(linha) if isinstance(v, str) and v.strip()}
    if "valor contabil" not in rotulos.values() or "nota" not in rotulos.values():
        return None
    mapa, codigos = {}, 0
    for i, r in rotulos.items():
        if r == "codigo":
            mapa["codigo" if codigos == 0 else "cod_participante"] = i
            codigos += 1
        elif r in COLUNAS_NOTA and COLUNAS_NOTA[r] not in mapa:
            mapa[COLUNAS_NOTA[r]] = i
    return mapa


def ler_notas(linhas: list[list], tipo: str, arquivo: str) -> Relatorio:
    rel = Relatorio(tipo=tipo, arquivo=arquivo)
    _cabecalho(linhas, rel)
    registros, mapa, ultimo = [], None, None

    def pegar(linha, chave):
        i = mapa.get(chave)
        return linha[i] if i is not None and i < len(linha) else None

    for linha in linhas:
        novo = _mapa_cabecalho(linha)
        if novo:
            mapa = novo
            continue
        if mapa is None:
            continue
        txt = normalizar(texto_linha(linha))
        if txt.startswith("total"):
            ultimo = None
            continue
        d = data(pegar(linha, "data"))
        valor = numero(pegar(linha, "valor"))
        imposto = normalizar(pegar(linha, "imposto"))
        if d and valor is not None:
            cfop = so_digitos(pegar(linha, "cfop"))
            ultimo = {
                "data": d, "competencia": pd.Period(d, "M"), "nota": texto_codigo(pegar(linha, "nota")),
                "serie": texto_codigo(pegar(linha, "serie")), "especie": texto_codigo(pegar(linha, "especie")),
                "participante": str(pegar(linha, "participante") or "").strip(),
                "cfop": cfop[:4] if cfop else "", "acumulador": so_digitos(pegar(linha, "acumulador")),
                "uf": str(pegar(linha, "uf") or "").strip(), "valor": valor, "impostos": {},
            }
            registros.append(ultimo)
            if imposto:
                ultimo["impostos"][imposto] = numero(pegar(linha, "valor_imposto")) or 0.0
        elif ultimo is not None and imposto:   # linha de continuação: IPI, DIFAL, ISS Ret...
            ultimo["impostos"][imposto] = numero(pegar(linha, "valor_imposto")) or 0.0
    if mapa is None:
        raise ValueError(f"{arquivo}: cabeçalho com 'Nota' e 'Valor Contábil' não encontrado.")
    df = pd.DataFrame(registros)
    if not df.empty:
        for imp in sorted({k for r in registros for k in r["impostos"]}):
            df[f"imp_{imp}"] = [r["impostos"].get(imp, 0.0) for r in registros]
        df = df.drop(columns="impostos")
        if rel.inicio is None:
            rel.inicio, rel.fim = df["data"].min(), df["data"].max()
    # total geral impresso no relatório, para conferência
    for i, linha in enumerate(linhas):
        if normalizar(texto_linha(linha)).startswith("total geral") and mapa:
            for prox in linhas[i + 1:i + 3]:
                v = numero(prox[mapa["valor"]]) if mapa["valor"] < len(prox) else None
                if v is not None:
                    rel.extras["total_geral"] = v
                    break
    rel.dados = df
    return rel


# --------------------------------------------------------------------------
# Folha – Extrato Mensal
# --------------------------------------------------------------------------
def ler_folha(linhas: list[list], arquivo: str) -> Relatorio:
    rel = Relatorio(tipo="folha", arquivo=arquivo)
    _cabecalho(linhas, rel)
    pessoas, atual, comp, calculo = [], None, None, ""
    for linha in linhas:
        r = _rotulos(linha)
        txt = normalizar(texto_linha(linha))
        if "competencia" in r:
            d = data(r["competencia"]) or (datas_no_texto(r["competencia"]) or [None])[0]
            comp = pd.Period(d, "M") if d else comp
            continue
        if "calculo" in r:
            calculo = str(r["calculo"])
        chave = "contr" if "contr" in r else ("empr." if "empr." in r else None)
        if chave:
            vals = [v for v in linha if v not in (None, "")]
            i = next(k for k, v in enumerate(vals) if normalizar(v).rstrip(":") == chave)
            nome = next((v for v in vals[i + 2:i + 3] if isinstance(v, str)), "")
            atual = {"competencia": comp, "calculo": calculo, "categoria": "contribuinte" if chave == "contr" else "empregado",
                     "codigo": vals[i + 1] if i + 1 < len(vals) else "", "nome": str(nome).strip(),
                     "cpf": so_digitos(r.get("cpf")), "situacao": str(r.get("situacao") or ""),
                     "vinculo": "", "proventos": 0.0, "base_inss": 0.0, "base_fgts": 0.0, "fgts": 0.0,
                     "demissao": None}
            pessoas.append(atual)
            continue
        if atual is None:
            continue
        if "vinculo" in r:
            atual["vinculo"] = str(r["vinculo"] or "").strip()
        if "proventos" in r and not txt.startswith("total"):
            atual["proventos"] = numero(r["proventos"]) or 0.0
        if "base inss" in r:
            atual["base_inss"] = numero(r["base inss"]) or 0.0
        if "base fgts" in r:
            atual["base_fgts"] = numero(r["base fgts"]) or 0.0
        if "valor fgts" in r:
            atual["fgts"] = numero(r["valor fgts"]) or 0.0
        if txt.startswith("demitido em"):
            d = datas_no_texto(texto_linha(linha))
            atual["demissao"] = d[0] if d else None
        if "total geral proventos" in r and comp is not None:
            rel.extras.setdefault("total_proventos", {})[str(comp)] = \
                rel.extras.get("total_proventos", {}).get(str(comp), 0.0) + (numero(r["total geral proventos"]) or 0.0)
    df = pd.DataFrame(pessoas)
    if df.empty:
        raise ValueError(f"{arquivo}: nenhum empregado/contribuinte encontrado no Extrato Mensal.")
    if df["competencia"].isna().any():
        raise ValueError(f"{arquivo}: há blocos sem 'Competência:' identificada.")
    rel.inicio = df["competencia"].min().start_time.date()
    rel.fim = df["competencia"].max().end_time.date()
    rel.dados = df
    return rel


# --------------------------------------------------------------------------
# DRE
# --------------------------------------------------------------------------
CLASSIF = re.compile(r"^\d+(\.\d+)+$")


def ler_dre(linhas: list[list], arquivo: str) -> Relatorio:
    rel = Relatorio(tipo="dre", arquivo=arquivo)
    _cabecalho(linhas, rel)
    idx = None
    contas = []
    for linha in linhas:
        txt = normalizar(texto_linha(linha))
        if "demonstracao do resultado" in txt:
            d = datas_no_texto(texto_linha(linha))
            if len(d) >= 2:
                rel.inicio, rel.fim = d[0], d[-1]
            elif d:
                rel.fim = d[0]
                rel.inicio = dt.date(d[0].year, 1, 1)   # DRE do exercício: acumulada desde janeiro
                rel.extras["acumulada_desde_janeiro"] = True
            continue
        rot = {normalizar(v): i for i, v in enumerate(linha) if isinstance(v, str) and v.strip()}
        if "classificacao" in rot and "saldo" in rot:
            idx = {"codigo": rot.get("codigo", 0), "classif": rot["classificacao"], "saldo": rot["saldo"]}
            continue
        if idx is None:
            continue
        classif = str(linha[idx["classif"]] or "").strip() if idx["classif"] < len(linha) else ""
        saldo = numero(linha[idx["saldo"]]) if idx["saldo"] < len(linha) else None
        if CLASSIF.match(classif) and saldo is not None:
            descricao = next((str(v).strip() for v in linha[idx["classif"] + 1:idx["saldo"]]
                              if isinstance(v, str) and v.strip()), "")
            contas.append({"codigo": so_digitos(linha[idx["codigo"]]), "classificacao": classif,
                           "descricao": descricao, "saldo": saldo})
        elif txt.startswith(("lucro liquido", "prejuizo liquido", "resultado liquido")):
            nums = [numero(v) for v in linha if numero(v) is not None]
            if nums:
                rel.extras["resultado_impresso"] = nums[-1]
    if idx is None:
        raise ValueError(f"{arquivo}: cabeçalho da DRE (Classificação / Saldo) não encontrado.")
    if rel.fim is None:
        raise ValueError(f"{arquivo}: não encontrei a data da DRE no título ('... EM dd/mm/aaaa').")
    rel.dados = pd.DataFrame(contas)
    return rel


# --------------------------------------------------------------------------
def ler_relatorio(caminho: str | Path) -> Relatorio:
    caminho = Path(caminho)
    linhas = ler_planilha(caminho)
    tipo = identificar(linhas)
    if tipo is None:
        raise ValueError(f"{caminho.name}: não reconheci o relatório (esperado Acompanhamento de "
                         "Serviços/Entradas/Saídas, Extrato Mensal da folha ou D.R.E.).")
    if tipo in ("servicos", "entradas", "saidas"):
        return ler_notas(linhas, tipo, caminho.name)
    if tipo == "folha":
        return ler_folha(linhas, caminho.name)
    return ler_dre(linhas, caminho.name)
