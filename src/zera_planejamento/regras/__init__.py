"""
Regras tributárias parametrizadas.

Tudo que é lei, alíquota, faixa ou data está aqui (ou em ``regras/dados/``),
com a base legal. Valores que dependem de ato ainda não publicado ou de
interpretação estão marcados ``[CONFERIR]`` e aparecem na lista
``pendencias_conferir()`` (mostrada no app e no relatório).

Módulos
-------
simples    LC 123/2006 — Anexos I a V, RBT12/FS12, Fator R, limites.
federais   Lucro Presumido (Lei 9.249/95, LC 224/2025), Lucro Real, PIS/Cofins, encargos.
reforma    EC 132/2023 e LC 214/2025 — CBS/IBS 2026–2033 e partilha do Simples.
"""
from .federais import RegrasFederais
from .reforma import RegrasReforma
from .simples import ANEXOS, aliquota_efetiva


def pendencias_conferir() -> list[str]:
    return [
        "CBS: alíquota de referência de 2027 ainda não fixada pelo Senado (prazo 15/12/2026). Padrão 9,21% "
        "(estimativa CGIBS, alíquota-padrão conjunta de 27,91%).",
        "IBS: alíquota de referência a partir de 2029 é estimativa (18,70%).",
        "Partilha do Simples com CBS/IBS (2027–2033): Anexo III copiado do motor Zera e Anexo I de publicação "
        "especializada; conferir com os anexos da LC 214/2025. Anexos II, IV e V sem tabela: o Simples híbrido "
        "não é calculado para eles.",
        "LC 224/2025: acréscimo de 10% na presunção do Presumido tem questionamento judicial.",
        "Fator R: inclusão da CPP recolhida no DAS na folha é opção do cliente (padrão: não incluir).",
        "Sublimite de R$ 3,6 mi: com RBT12 na 6ª faixa e empresa ainda não impedida, ICMS/ISS ficam fora do DAS; "
        "conferir a regra da Res. CGSN 140/2018, art. 25. Partilha de ICMS/ISS de 2026 transcrita dos Anexos da LC 123.",
        "Lei 15.270/2025: redutor do IRPFM (carga PJ + PF até 34%), restituição do IRRF de 10% excedente e "
        "alíquota efetiva da PJ no Simples (o sistema usa 0%, o que pode superestimar o IRPFM) dependem de "
        "regulamentação. A retenção sobre lucros de empresa do Simples tem divergência de entendimento.",
        "Tabelas de 2026 da pessoa física (salário mínimo R$ 1.621,00, teto do INSS R$ 8.475,55, IRRF da "
        "Lei 15.191/2025): conferir a atualização anual.",
        "Prazos de opção do Simples híbrido (IBS/CBS por fora): conferir a resolução do CGSN vigente.",
    ]


__all__ = ["RegrasFederais", "RegrasReforma", "ANEXOS", "aliquota_efetiva", "pendencias_conferir"]
