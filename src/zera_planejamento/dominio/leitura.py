"""
Leitura bruta das planilhas exportadas pelo Domínio.

O Domínio grava um .xls (BIFF) fora do padrão que o xlrd recusa. O
python-calamine lê esse formato sem conversão, inclusive no Windows. Se ele
falhar, tenta o LibreOffice (soffice) para converter em .xlsx.

Todas as funções devolvem a planilha como lista de linhas (listas de células),
e os leitores de relatório localizam as colunas pelos RÓTULOS, não por posição
fixa — assim o layout pode variar um pouco entre versões do Domínio.
"""
from __future__ import annotations

import datetime as dt
import re
import shutil
import subprocess
import tempfile
import unicodedata
from pathlib import Path

Linhas = list[list]


def normalizar(texto) -> str:
    """Minúsculas, sem acento e sem espaços repetidos (para comparar rótulos)."""
    if texto is None:
        return ""
    t = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", t).strip().lower()


def _soffice() -> str | None:
    for nome in ("soffice", "libreoffice"):
        if shutil.which(nome):
            return shutil.which(nome)
    for caminho in (r"C:\Program Files\LibreOffice\program\soffice.exe",
                    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"):
        if Path(caminho).exists():
            return caminho
    return None


def _via_calamine(caminho: Path) -> Linhas:
    from python_calamine import CalamineWorkbook
    wb = CalamineWorkbook.from_path(str(caminho))
    return wb.get_sheet_by_index(0).to_python()


def _via_openpyxl(caminho: Path) -> Linhas:
    import openpyxl
    wb = openpyxl.load_workbook(caminho, data_only=True, read_only=True)
    ws = wb.worksheets[0]
    return [list(r) for r in ws.iter_rows(values_only=True)]


def ler_planilha(caminho: str | Path) -> Linhas:
    """Primeira aba do arquivo como lista de linhas."""
    caminho = Path(caminho)
    if not caminho.exists():
        raise FileNotFoundError(caminho)
    erros = []
    try:
        return _via_calamine(caminho)
    except Exception as e:  # noqa: BLE001
        erros.append(f"calamine: {e}")
    if caminho.suffix.lower() in (".xlsx", ".xlsm"):
        try:
            return _via_openpyxl(caminho)
        except Exception as e:  # noqa: BLE001
            erros.append(f"openpyxl: {e}")
    soffice = _soffice()
    if soffice:
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run([soffice, "--headless", "--calc", "--convert-to", "xlsx", "--outdir", tmp, str(caminho)],
                           capture_output=True, timeout=180)
            convertido = Path(tmp) / (caminho.stem + ".xlsx")
            if convertido.exists():
                return _via_openpyxl(convertido)
        erros.append("LibreOffice não converteu o arquivo")
    raise ValueError(f"Não consegui ler {caminho.name}. Tentativas: {'; '.join(erros)}. "
                     "Abra no Excel e salve como .xlsx, ou instale: pip install python-calamine")


# --------------------------------------------------------------------------
# Conversões
# --------------------------------------------------------------------------
def numero(v) -> float | None:
    """Converte 1621.0, '1.621,00', '(10,00)', '-' em float."""
    if v is None or v == "":
        return None
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace("R$", "").replace("\u00a0", "").replace(" ", "")
    if s in ("", "-", "--"):
        return None
    negativo = s.startswith("(") and s.endswith(")")
    s = s.strip("()")
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    try:
        n = float(s)
    except ValueError:
        return None
    return -n if negativo else n


def data(v) -> dt.date | None:
    if isinstance(v, dt.datetime):
        return v.date()
    if isinstance(v, dt.date):
        return v
    if isinstance(v, str):
        m = re.search(r"(\d{2})/(\d{2})/(\d{4})", v)
        if m:
            return dt.date(int(m[3]), int(m[2]), int(m[1]))
    return None


def datas_no_texto(texto: str) -> list[dt.date]:
    return [dt.date(int(a), int(m), int(d)) for d, m, a in re.findall(r"(\d{2})/(\d{2})/(\d{4})", str(texto))]


def so_digitos(v) -> str:
    """Só os dígitos; números inteiros lidos como float (6552.0) não ganham o zero do decimal."""
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return re.sub(r"\D", "", str(v if v is not None else ""))


def texto_codigo(v) -> str:
    """Código/número como texto: 900.0 -> '900'; None -> ''."""
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return str(v).strip()


def texto_linha(linha: list) -> str:
    return " ".join(str(c) for c in linha if c not in (None, ""))
