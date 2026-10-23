"""
Simples Nacional — LC 123/2006 (redação LC 155/2016 e LC 214/2025), Res. CGSN 140/2018.

RBT12 e FS12
------------
- Até dez/2026: receita bruta (e folha) dos 12 meses anteriores ao período de
  apuração (LC 123, art. 18, § 1º).
- A partir de jan/2027: 12 meses antecedentes ao **mês anterior** ao período de
  apuração — o mês imediatamente anterior sai da conta (art. 18 alterado pela
  LC 214/2025). Ex.: PA maio/2027 → abr/2026 a mar/2027.

Sublimite de R$ 3,6 mi (art. 13-A e art. 20, §§ 1º e 1º-A)
----------------------------------------------------------
- Receita do ano-calendário anterior acima de R$ 3,6 mi: ICMS/ISS fora do DAS o ano todo.
- Receita acumulada no ano acima de R$ 3,6 mi: fora do DAS a partir do mês seguinte se o
  excesso passar de 20% (R$ 4,32 mi); senão, a partir de janeiro do ano seguinte.
- Impedida, a empresa recolhe o DAS sem o percentual de ICMS/ISS da repartição
  (``dados/simples_partilha_icms_iss.csv``) e apura ICMS/ISS pelas regras normais.
- RBT12 na 6ª faixa: a repartição não tem ICMS/ISS, que ficam fora do DAS
  [CONFERIR: Res. CGSN 140/2018, art. 25, quando a RBT12 passa do sublimite sem impedimento].
"""
from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path

import pandas as pd

# (limite superior da RBT12, alíquota nominal, parcela a deduzir)
ANEXOS: dict[str, list[tuple[float, float, float]]] = {
    "I": [(180_000, 0.040, 0), (360_000, 0.073, 5_940), (720_000, 0.095, 13_860), (1_800_000, 0.107, 22_500),
          (3_600_000, 0.143, 87_300), (4_800_000, 0.190, 378_000)],
    "II": [(180_000, 0.045, 0), (360_000, 0.078, 5_940), (720_000, 0.100, 13_860), (1_800_000, 0.112, 22_500),
           (3_600_000, 0.147, 85_500), (4_800_000, 0.300, 720_000)],
    "III": [(180_000, 0.060, 0), (360_000, 0.112, 9_360), (720_000, 0.135, 17_640), (1_800_000, 0.160, 35_640),
            (3_600_000, 0.210, 125_640), (4_800_000, 0.330, 648_000)],
    "IV": [(180_000, 0.045, 0), (360_000, 0.090, 8_100), (720_000, 0.102, 12_420), (1_800_000, 0.140, 39_780),
           (3_600_000, 0.220, 183_780), (4_800_000, 0.330, 828_000)],
    "V": [(180_000, 0.155, 0), (360_000, 0.180, 4_500), (720_000, 0.195, 9_900), (1_800_000, 0.205, 17_100),
          (3_600_000, 0.230, 62_100), (4_800_000, 0.305, 540_000)],
}
LIMITE_RECEITA = 4_800_000.0       # art. 3º, II
LIMITE_EXCESSO = 0.20              # art. 3º, §§ 9º e 9º-A: excesso > 20% exclui no mês seguinte
SUBLIMITE_ICMS_ISS = 3_600_000.0   # art. 13-A
FATOR_R_CORTE = 0.28               # art. 18, § 5º-J e § 5º-M
INICIO_RBT12_DEFASADA = pd.Period("2027-01", "M")


def aliquota_efetiva(rbt12: float, anexo: str) -> tuple[float, int]:
    """(alíquota efetiva, faixa 1–6). Faixa 7 = acima de R$ 4,8 mi (só referência)."""
    tabela = ANEXOS[anexo]
    if rbt12 <= 0:
        return tabela[0][1], 1
    for faixa, (limite, nominal, deduzir) in enumerate(tabela, start=1):
        if rbt12 <= limite:
            return max((rbt12 * nominal - deduzir) / rbt12, 0.0), faixa
    _, nominal, deduzir = tabela[-1]
    return (rbt12 * nominal - deduzir) / rbt12, 7


ISS_EFETIVO_MAXIMO = 0.05          # Anexos III e IV, nota da 5ª faixa: ISS efetivo no DAS até 5%


@lru_cache(maxsize=1)
def _partilha_icms_iss() -> dict[tuple[str, int], float]:
    with open(Path(__file__).parent / "dados" / "simples_partilha_icms_iss.csv", encoding="utf-8") as f:
        return {(linha["anexo"], int(linha["faixa"])): float(linha["percentual"]) for linha in csv.DictReader(f)}


def percentual_icms_iss(anexo: str, faixa: int) -> float:
    """Fração do DAS que é ICMS (Anexos I e II) ou ISS (III, IV e V) na repartição de 2026."""
    return _partilha_icms_iss().get((anexo, min(faixa, 6)), 0.0)


def janela_rbt12(pa: pd.Period) -> tuple[pd.Period, pd.Period]:
    """Primeiro e último mês que compõem a RBT12/FS12 do período de apuração ``pa``."""
    if pa >= INICIO_RBT12_DEFASADA:
        return pa - 13, pa - 2
    return pa - 12, pa - 1
