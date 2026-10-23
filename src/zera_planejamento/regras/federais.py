"""
Regras federais fora do Simples.

Lucro Presumido
    Lei 9.249/1995, art. 15 e 20 (presunção); Lei 9.430/1996, art. 1º, 3º e 25 (trimestre,
    adicional, receitas financeiras); Lei 9.718/1998 (PIS/Cofins cumulativos).
    LC 224/2025, art. 4º + IN RFB 2.305/2025 e 2.306/2026: acréscimo de 10% nos percentuais de
    presunção sobre a receita que exceder R$ 5 mi/ano; controle trimestral de R$ 1,25 mi com
    aproveitamento do saldo e ajuste no 4º trimestre; IRPJ desde 01/2026 e CSLL desde 04/2026
    (noventena). Tema com questionamento judicial.
Lucro Real
    Leis 10.637/2002 e 10.833/2003 (PIS 1,65% / Cofins 7,6% não cumulativos); Lei 14.592/2023
    (sem ICMS na base do crédito); Decreto 8.426/2015 (receitas financeiras 0,65% + 4%);
    Lei 8.981/1995, art. 42 e Lei 9.065/1995, art. 15 (compensação limitada a 30%).
Tema 69/STF
    ICMS destacado fora da base de PIS/Cofins.
Encargos sobre a folha (fora do Simples)
    Lei 8.212/1991, art. 22: 20% sobre salários e pró-labore; RAT (1/2/3%) × FAP e Terceiros
    só sobre a folha de empregados.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# Colunas de receita da base mensal -> presunção (IRPJ, CSLL)
PRESUNCAO_PADRAO = {
    "rec_anexo_i": (0.08, 0.12),     # comércio
    "rec_anexo_ii": (0.08, 0.12),    # indústria
    "rec_anexo_iii": (0.32, 0.32),   # serviços em geral
    "rec_anexo_iv": (0.32, 0.32),
    "rec_anexo_v": (0.32, 0.32),
    "rec_fator_r": (0.32, 0.32),
}


@dataclass
class RegrasFederais:
    presuncao: dict[str, tuple[float, float]] = field(default_factory=lambda: dict(PRESUNCAO_PADRAO))
    irpj: float = 0.15
    irpj_adicional: float = 0.10
    irpj_limite_adicional_mes: float = 20_000.0
    csll: float = 0.09
    pis_cumulativo: float = 0.0065
    cofins_cumulativo: float = 0.03
    pis_nao_cumulativo: float = 0.0165
    cofins_nao_cumulativo: float = 0.076
    pis_cofins_receita_financeira: float = 0.0465
    excluir_icms_base_pis_cofins: bool = True       # Tema 69
    trava_compensacao: float = 0.30
    # LC 224/2025
    lc224_ativo: bool = True
    lc224_acrescimo: float = 0.10
    lc224_limite_trimestral: float = 1_250_000.0
    lc224_inicio_irpj: str = "2026-01"
    lc224_inicio_csll: str = "2026-04"
    # encargos
    cpp: float = 0.20
    limite_lucro_presumido: float = 78_000_000.0

    @property
    def pis_cofins_nao_cumulativo(self) -> float:
        return self.pis_nao_cumulativo + self.cofins_nao_cumulativo

    @property
    def pis_cofins_cumulativo(self) -> float:
        return self.pis_cumulativo + self.cofins_cumulativo
