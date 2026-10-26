"""
Reforma Tributária do consumo — EC 132/2023 e LC 214/2025.

Calendário usado (por ano-calendário da competência):

| Ano  | PIS/Cofins | CBS                          | IBS                        | ICMS/ISS |
|------|-----------|------------------------------|----------------------------|----------|
| 2026 | vigentes  | 0,9% teste (sem custo)        | 0,1% teste (sem custo)      | 100%     |
| 2027 | extintos  | referência − 0,1 p.p.        | 0,1%                       | 100%     |
| 2028 | extintos  | referência − 0,1 p.p.        | 0,1%                       | 100%     |
| 2029 | extintos  | referência                   | 10% da referência          | 90%      |
| 2030 |           |                              | 20%                        | 80%      |
| 2031 |           |                              | 30%                        | 70%      |
| 2032 |           |                              | 40%                        | 60%      |
| 2033 |           |                              | 100%                       | 0%       |

- Em 2026 a CBS/IBS de teste é compensável/dispensada: custo zero no modelo.
- CBS e IBS são "por fora": não integram a receita nem a base presumida.
- Até 2032, ICMS e ISS não entram na base da CBS/IBS (LC 214, art. 12, § 2º).
- Alíquotas de referência são **editáveis** [CONFERIR]: o Senado fixa a de 2027
  até 15/12/2026.

Partilha do Simples (quanto do DAS é CBS/IBS) fica em
``dados/simples_partilha_reforma.csv`` (por ano, anexo e faixa).
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

DADOS = Path(__file__).parent / "dados"
FRACAO_IBS = {2029: 0.10, 2030: 0.20, 2031: 0.30, 2032: 0.40}
FATOR_ICMS_ISS = {2029: 0.90, 2030: 0.80, 2031: 0.70, 2032: 0.60}


@dataclass
class RegrasReforma:
    ativa: bool = True
    cbs_referencia: float = 0.0921           # [CONFERIR] Senado até 15/12/2026
    ibs_referencia: float = 0.187            # [CONFERIR] estimativa CGIBS
    reducao_cbs_2027_2028: float = 0.001     # LC 214, art. 347
    ibs_2027_2028: float = 0.001             # 0,05% estadual + 0,05% municipal
    credito_imobilizado: bool = True         # CBS/IBS: crédito integral na aquisição de ativo
    sobrescrever: dict[int, dict[str, float]] = field(default_factory=dict)   # {ano: {"cbs":..,"ibs":..}}
    # Regimes diferenciados (LC 214/2025): redução das alíquotas de IBS/CBS sobre as VENDAS do contribuinte —
    # 30% (profissões intelectuais regulamentadas), 60% (saúde, educação, insumos agropecuários e outros),
    # 100% (alíquota zero). O crédito das compras continua pela alíquota cheia cobrada do fornecedor.
    # [CONFERIR artigo, requisitos e lista de atividades no caso de cada cliente]
    reducao_aliquota: float = 0.0

    def pis_cofins_vigente(self, ano: int) -> bool:
        return not self.ativa or ano <= 2026

    def cbs(self, ano: int) -> float:
        if not self.ativa or ano <= 2026:
            return 0.0
        if ano in self.sobrescrever and "cbs" in self.sobrescrever[ano]:
            return self.sobrescrever[ano]["cbs"]
        if ano <= 2028:
            return self.cbs_referencia - self.reducao_cbs_2027_2028
        return self.cbs_referencia

    def ibs(self, ano: int) -> float:
        if not self.ativa or ano <= 2026:
            return 0.0
        if ano in self.sobrescrever and "ibs" in self.sobrescrever[ano]:
            return self.sobrescrever[ano]["ibs"]
        if ano <= 2028:
            return self.ibs_2027_2028
        if ano >= 2033:
            return self.ibs_referencia
        return self.ibs_referencia * FRACAO_IBS[ano]

    def fator_icms_iss(self, ano: int) -> float:
        """Fração do ICMS/ISS ainda cobrada no ano (redução gradual 2029–2032, extinção em 2033)."""
        if not self.ativa or ano <= 2028:
            return 1.0
        if ano >= 2033:
            return 0.0
        return FATOR_ICMS_ISS[ano]


@lru_cache(maxsize=1)
def _partilha() -> dict[tuple[int, str, int], dict[str, float]]:
    tabela = {}
    with open(DADOS / "simples_partilha_reforma.csv", encoding="utf-8") as f:
        for linha in csv.DictReader(f):
            chave = (int(linha["ano"]), linha["anexo"], int(linha["faixa"]))
            tabela[chave] = {k: float(linha[k]) for k in ("irpj", "csll", "cbs", "ibs", "cpp", "icms", "iss")}
    return tabela


def partilha_simples(ano: int, anexo: str, faixa: int) -> dict[str, float] | None:
    """Percentuais de repartição do DAS (ano ≥ 2027). ``None`` se a tabela não tiver o anexo/ano."""
    if ano < 2027:
        return None
    ano = min(ano, 2033)
    return _partilha().get((ano, anexo, min(faixa, 6)))
