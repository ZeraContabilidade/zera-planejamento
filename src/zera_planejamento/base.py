"""
Base mensal do cliente: uma linha por competência, colunas canônicas.

Convenções
----------
- Valores em R$ por competência. Vazio (NaN) = não informado.
- Receitas por **anexo do Simples**; o Presumido usa a mesma separação para a presunção.
- ``custos`` e ``despesas`` vêm da contabilidade **sem** tributos sobre a receita, **sem** folha
  (salários, pró-labore, FGTS) e **sem** encargos patronais: o motor calcula esses itens por regime.
- As colunas ``cred_*``, ``uso_consumo`` e ``imobilizado`` são a **base de crédito** (aquisições com
  nota). Elas não entram de novo no resultado: já estão dentro de custos/despesas da DRE.
- ``icms_*`` e ``iss`` só valem se o cliente está fora do Simples; no Simples o motor estima pelas
  alíquotas do cadastro.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

COLUNAS: dict[str, tuple[str, str]] = {
    # coluna: (grupo, descrição)
    "rec_anexo_i": ("receita", "Receita — comércio (Anexo I)"),
    "rec_anexo_ii": ("receita", "Receita — indústria (Anexo II)"),
    "rec_anexo_iii": ("receita", "Receita — serviços (Anexo III)"),
    "rec_anexo_iv": ("receita", "Receita — serviços (Anexo IV)"),
    "rec_anexo_v": ("receita", "Receita — serviços (Anexo V)"),
    "rec_fator_r": ("receita", "Receita — serviços sujeitos ao Fator R (III/V)"),
    "devolucoes": ("receita", "Devoluções e cancelamentos"),
    "icms_debito": ("tributos", "ICMS destacado nas saídas (fora do Simples)"),
    "icms_credito": ("tributos", "ICMS creditado nas entradas (fora do Simples)"),
    "iss": ("tributos", "ISS do mês (fora do Simples)"),
    "cred_insumos": ("credito", "Insumos e mercadorias (crédito PIS/Cofins e CBS/IBS)"),
    "cred_energia": ("credito", "Energia elétrica (crédito PIS/Cofins e CBS/IBS)"),
    "cred_aluguel": ("credito", "Aluguel de PJ (crédito PIS/Cofins e CBS/IBS)"),
    "cred_servicos": ("credito", "Serviços de PJ (crédito PIS/Cofins e CBS/IBS)"),
    "cred_fretes": ("credito", "Fretes (crédito PIS/Cofins e CBS/IBS)"),
    "uso_consumo": ("credito", "Uso, consumo e comunicação (só crédito CBS/IBS)"),
    "imobilizado": ("credito", "Imobilizado (crédito CBS/IBS na aquisição)"),
    "salarios": ("folha", "Salários de empregados (base INSS)"),
    "pro_labore": ("folha", "Pró-labore e contribuintes individuais"),
    "fgts": ("folha", "FGTS"),
    "cpp_das": ("folha", "CPP recolhida no DAS (só para o Fator R, se marcado)"),
    "custos": ("resultado", "Custos (CSP/CMV) — sem tributos e sem folha"),
    "despesas": ("resultado", "Despesas operacionais — sem tributos e sem folha"),
    "receitas_financeiras": ("resultado", "Receitas financeiras"),
    "adicoes": ("resultado", "Adições do LALUR (indedutíveis)"),
    "exclusoes": ("resultado", "Exclusões do LALUR"),
}
RECEITAS = [c for c, (g, _) in COLUNAS.items() if g == "receita" and c != "devolucoes"]
CREDITO_PIS_COFINS = ["cred_insumos", "cred_energia", "cred_aluguel", "cred_servicos", "cred_fretes"]
CREDITO_SO_CBS = ["uso_consumo"]


@dataclass
class BaseMensal:
    dados: pd.DataFrame      # índice PeriodIndex mensal contínuo, colunas = COLUNAS
    origem: pd.DataFrame     # mesma forma: texto com a origem de cada valor

    # ---------------- construção ----------------
    @classmethod
    def vazia(cls, inicio: str | pd.Period | None = None, fim: str | pd.Period | None = None) -> "BaseMensal":
        idx = pd.period_range(inicio, fim, freq="M", name="competencia") if inicio else \
            pd.PeriodIndex([], freq="M", name="competencia")
        return cls(pd.DataFrame(np.nan, index=idx, columns=list(COLUNAS)),
                   pd.DataFrame("", index=idx, columns=list(COLUNAS)))

    @classmethod
    def de_dataframe(cls, df: pd.DataFrame, origem: str = "manual") -> "BaseMensal":
        b = cls.vazia()
        b.mesclar(df, origem)
        return b

    def _expandir(self, inicio: pd.Period, fim: pd.Period) -> None:
        atual = self.dados.index
        ini = min([inicio] + ([atual.min()] if len(atual) else []))
        fi = max([fim] + ([atual.max()] if len(atual) else []))
        idx = pd.period_range(ini, fi, freq="M", name="competencia")
        self.dados = self.dados.reindex(idx)
        self.origem = self.origem.reindex(idx).fillna("")

    def mesclar(self, parcial: pd.DataFrame, origem: str) -> list[tuple[pd.Period, str]]:
        """Grava as células não vazias de ``parcial`` (índice Period). Devolve as células alteradas."""
        parcial = parcial.copy()
        if not isinstance(parcial.index, pd.PeriodIndex):
            parcial.index = pd.PeriodIndex(parcial.index, freq="M")
        desconhecidas = set(parcial.columns) - set(COLUNAS)
        if desconhecidas:
            raise ValueError(f"Colunas desconhecidas na base: {sorted(desconhecidas)}")
        if parcial.empty:
            return []
        self._expandir(parcial.index.min(), parcial.index.max())
        alteradas = []
        for col in parcial.columns:
            serie = parcial[col].dropna()
            for per, valor in serie.items():
                self.dados.at[per, col] = float(valor)
                self.origem.at[per, col] = origem
                alteradas.append((per, col))
        return alteradas

    # ---------------- consultas ----------------
    @property
    def meses(self) -> pd.PeriodIndex:
        return self.dados.index

    def receita_bruta(self) -> pd.Series:
        d = self.dados
        return (d[RECEITAS].sum(axis=1, min_count=1).fillna(0) - d["devolucoes"].fillna(0)).clip(lower=0)

    def meses_com(self, grupo: str) -> pd.PeriodIndex:
        cols = [c for c, (g, _) in COLUNAS.items() if g == grupo]
        return self.dados.index[self.dados[cols].notna().any(axis=1)]

    def recorte(self, inicio: pd.Period | None = None, fim: pd.Period | None = None) -> "BaseMensal":
        m = self.dados.index
        sel = (m >= inicio if inicio is not None else True) & (m <= fim if fim is not None else True)
        return BaseMensal(self.dados.loc[sel].copy(), self.origem.loc[sel].copy())

    def copia(self) -> "BaseMensal":
        return BaseMensal(self.dados.copy(), self.origem.copy())

    # ---------------- persistência ----------------
    def salvar(self, pasta: Path) -> None:
        pasta.mkdir(parents=True, exist_ok=True)
        d = self.dados.copy()
        d.index = d.index.astype(str)
        d.to_csv(pasta / "base_mensal.csv", sep=";", decimal=",", encoding="utf-8-sig")
        o = self.origem.copy()
        o.index = o.index.astype(str)
        o.to_csv(pasta / "base_origem.csv", sep=";", encoding="utf-8-sig")

    @classmethod
    def carregar(cls, pasta: Path) -> "BaseMensal":
        arq = pasta / "base_mensal.csv"
        if not arq.exists():
            return cls.vazia()
        d = pd.read_csv(arq, sep=";", decimal=",", index_col=0, encoding="utf-8-sig")
        d.index = pd.PeriodIndex(d.index, freq="M", name="competencia")
        d = d.reindex(columns=list(COLUNAS)).astype(float)
        o_arq = pasta / "base_origem.csv"
        if o_arq.exists():
            o = pd.read_csv(o_arq, sep=";", index_col=0, encoding="utf-8-sig", dtype=str).fillna("")
            o.index = pd.PeriodIndex(o.index, freq="M", name="competencia")
            o = o.reindex(index=d.index, columns=list(COLUNAS)).fillna("")
        else:
            o = pd.DataFrame("", index=d.index, columns=list(COLUNAS))
        b = cls(d, o)
        b._expandir(d.index.min(), d.index.max()) if len(d) else None
        return b

    # ---------------- planilha de digitação ----------------
    def para_planilha(self, caminho: Path) -> Path:
        """Planilha com uma linha por mês para digitar/ajustar valores manualmente."""
        d = self.dados.copy()
        d.index = d.index.astype(str)
        d.columns = [f"{c} | {COLUNAS[c][1]}" for c in d.columns]
        d.to_excel(caminho, sheet_name="Base mensal")
        return caminho

    @staticmethod
    def de_planilha(caminho: Path) -> pd.DataFrame:
        df = pd.read_excel(caminho, sheet_name=0, index_col=0, engine="openpyxl")
        df.columns = [str(c).split(" | ")[0].strip() for c in df.columns]
        df = df[[c for c in df.columns if c in COLUNAS]]
        df.index = pd.PeriodIndex(df.index.astype(str), freq="M", name="competencia")
        return df.apply(pd.to_numeric, errors="coerce")
