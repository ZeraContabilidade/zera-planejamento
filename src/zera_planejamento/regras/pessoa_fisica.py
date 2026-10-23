"""
Tributação do sócio pessoa física — pró-labore e lucros (2026).

Pró-labore
    INSS do contribuinte individual: 11% até o teto, retido pela empresa (Lei 8.212/1991, art. 21 e
    art. 30, § 4º; Lei 10.666/2003, art. 4º). Salário mínimo R$ 1.621,00 e teto R$ 8.475,55 (2026).
    IRRF pela tabela mensal (Lei 15.191/2025), com dedução do INSS e dependentes ou o desconto
    simplificado de R$ 607,20, o que for maior.
    Redução da Lei 15.270/2025 (desde 01/2026): até R$ 5.000/mês, redução de até R$ 312,89 (IR zero);
    de R$ 5.000,01 a R$ 7.350, redução = 978,62 − 0,133145 × rendimento; limitada ao imposto.
Lucros e dividendos — Lei 15.270/2025
    IRRF de 10% sobre o **total** pago no mês quando a mesma PJ paga mais de R$ 50 mil à mesma PF
    (antecipação do IRPFM).
    IRPFM (imposto mínimo anual): renda total acima de R$ 600 mil → alíquota (renda ÷ 60.000 − 10)%,
    10% a partir de R$ 1,2 mi. Deduz o IR da tabela progressiva e o redutor que impede a soma da
    alíquota efetiva da PJ (IRPJ + CSLL ÷ lucro contábil) com a do IRPFM de passar de 34%
    [CONFERIR: regulamentação do redutor, aplicação ao Simples e restituição do IRRF excedente].
"""
from __future__ import annotations

import math

SALARIO_MINIMO = 1_621.00
TETO_INSS = 8_475.55
INSS_CONTRIBUINTE_INDIVIDUAL = 0.11

# (limite superior da base, alíquota, parcela a deduzir) — Lei 15.191/2025
IRRF_TABELA = [(2_428.80, 0.0, 0.0), (2_826.65, 0.075, 182.16), (3_751.05, 0.15, 394.16),
               (4_664.68, 0.225, 675.49), (math.inf, 0.275, 908.73)]
DEDUCAO_DEPENDENTE = 189.59
DESCONTO_SIMPLIFICADO = 607.20
REDUCAO_ISENCAO_ATE = 5_000.00
REDUCAO_MAXIMA = 312.89
REDUCAO_ATE = 7_350.00
REDUCAO_A, REDUCAO_B = 978.62, 0.133145

DIVIDENDO_LIMITE_MES = 50_000.00
DIVIDENDO_IRRF = 0.10
IRPFM_INICIO = 600_000.00
IRPFM_CHEIO = 1_200_000.00
IRPFM_ALIQUOTA_MAX = 0.10
CARGA_COMBINADA_MAX = 0.34      # 40% seguradoras e 45% instituições financeiras (fora do escopo)


def inss_pro_labore(valor_mes: float) -> float:
    """11% sobre o pró-labore, limitado ao teto. Ex.: 10.000 → 11% × 8.475,55 = 932,31."""
    return INSS_CONTRIBUINTE_INDIVIDUAL * min(max(valor_mes, 0.0), TETO_INSS)


def reducao_lei_15270(rendimento_mes: float) -> float:
    if rendimento_mes <= REDUCAO_ISENCAO_ATE:
        return REDUCAO_MAXIMA
    if rendimento_mes <= REDUCAO_ATE:
        return max(0.0, REDUCAO_A - REDUCAO_B * rendimento_mes)
    return 0.0


def irrf_mensal(rendimento_mes: float, inss: float = 0.0, dependentes: int = 0) -> float:
    """IRRF da tabela mensal com a redução da Lei 15.270/2025."""
    if rendimento_mes <= 0:
        return 0.0
    deducoes = max(inss + dependentes * DEDUCAO_DEPENDENTE, DESCONTO_SIMPLIFICADO)
    base = max(0.0, rendimento_mes - deducoes)
    for limite, aliquota, deduzir in IRRF_TABELA:
        if base <= limite:
            imposto = max(0.0, base * aliquota - deduzir)
            break
    return round(max(0.0, imposto - min(imposto, reducao_lei_15270(rendimento_mes))), 2)


def irrf_dividendos(valor_mes: float) -> float:
    """10% sobre o total pago no mês pela mesma PJ à mesma PF, se acima de R$ 50 mil."""
    return DIVIDENDO_IRRF * valor_mes if valor_mes > DIVIDENDO_LIMITE_MES else 0.0


def aliquota_irpfm(renda_anual: float) -> float:
    """(renda ÷ 60.000 − 10)% entre R$ 600 mil e R$ 1,2 mi; 10% acima. Ex.: 900 mil → 5%."""
    if renda_anual <= IRPFM_INICIO:
        return 0.0
    if renda_anual >= IRPFM_CHEIO:
        return IRPFM_ALIQUOTA_MAX
    return (renda_anual / 60_000 - 10) / 100


def irpfm(renda_anual: float, dividendos_anuais: float, ir_tabela_anual: float, aliquota_pj: float) -> dict[str, float]:
    """IRPFM anual do sócio.

    bruto   = renda × alíquota
    redutor = dividendos × (alíquota PJ + alíquota IRPFM − 34%), se positivo, até o IRPFM dos dividendos
    devido  = máx(0, bruto − IR da tabela − redutor)
    O IRRF de 10% sobre dividendos é antecipação: abate do devido no ajuste anual.
    """
    aliq = aliquota_irpfm(renda_anual)
    bruto = renda_anual * aliq
    excesso = max(0.0, aliquota_pj + aliq - CARGA_COMBINADA_MAX)
    redutor = min(dividendos_anuais * excesso, dividendos_anuais * aliq)
    devido = max(0.0, bruto - ir_tabela_anual - redutor)
    return {"aliquota": aliq, "bruto": bruto, "redutor": redutor, "devido": devido}
