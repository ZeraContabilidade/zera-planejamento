"""
Diagnóstico de precisão: o quanto os dados do cliente sustentam os números do planejamento, e o que fazer para
torná-los mais precisos.

Cada verificação tem um peso (o impacto típico no resultado) e diz onde resolver. A nota é a soma dos pesos das
verificações atendidas (0–100). Não altera nenhum cálculo: só lê a base e o cadastro.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .base import BaseMensal
from .cliente import Cliente
from .regras.reforma import partilha_simples


@dataclass
class Verificacao:
    titulo: str
    ok: bool
    peso: int
    impacto: str          # o que fica impreciso se faltar
    como: str             # o que fazer
    pagina: str           # tela que resolve (caminho da página)


def diagnosticar(cliente: Cliente, base: BaseMensal) -> list[Verificacao]:
    d = base.dados
    rb = base.receita_bruta()
    reais = rb.index[rb > 0]
    ult12 = reais[-12:]
    n = len(reais)
    tem = lambda cols, meses: bool(len(meses)) and d.loc[meses, cols].notna().any(axis=1).all()  # noqa: E731
    dre_12 = tem(["custos", "despesas"], ult12)
    dre_algum = bool(len(ult12)) and d.loc[ult12, ["custos", "despesas"]].notna().any().any()
    folha = tem(["salarios", "pro_labore"], ult12)
    creditos = bool(len(ult12)) and d.loc[ult12, ["cred_insumos", "cred_energia", "cred_aluguel", "cred_servicos",
                                                   "cred_fretes", "uso_consumo"]].notna().any().any()
    fora_simples = cliente.regime_atual != "simples"
    icms_real = bool(len(ult12)) and d.loc[ult12, ["icms_debito", "iss"]].notna().any().any()
    anexos = {"rec_anexo_i": "I", "rec_anexo_ii": "II", "rec_anexo_iii": "III", "rec_anexo_iv": "IV",
              "rec_anexo_v": "V"}
    usados = {a for col, a in anexos.items() if col in d and d[col].fillna(0).sum() > 0}
    if d.get("rec_fator_r") is not None and d["rec_fator_r"].fillna(0).sum() > 0:
        usados |= {"III", "V"}
    sem_partilha = sorted(a for a in usados if partilha_simples(2027, a, 1) is None)
    encargos_padrao = (cliente.rat, cliente.fap, cliente.terceiros) == (0.02, 1.0, 0.058)
    # alíquotas do cadastro diferentes do padrão (ISS 5%, ICMS 18% / 12%) = conferidas pelo escritório
    aliquotas_conferidas = (cliente.iss_aliquota, cliente.icms_aliquota_saida, cliente.icms_aliquota_entrada) !=         (0.05, 0.18, 0.12)
    return [
        Verificacao("13 meses ou mais de receita", n >= 13, 18,
                    f"RBT12 e Fator R estimados pela média ({n} mês(es) com receita).",
                    "Importe os relatórios desde janeiro do ano anterior.", "paginas/importar.py"),
        Verificacao("DRE em todos os últimos 12 meses", dre_12, 18,
                    "Lucro Real e lucro distribuível dos sócios" + (" com meses sem custo" if dre_algum else " sem DRE")
                    + " — o Real fica superestimado.",
                    "Importe a DRE mês a mês (ou balancete), também do ano anterior.", "paginas/documentos.py"),
        Verificacao("Folha nos últimos 12 meses", folha, 12, "Fator R, encargos e pró-labore estimados.",
                    "Importe o Extrato Mensal da folha.", "paginas/importar.py"),
        Verificacao("Compras com crédito (Entradas)", creditos, 10,
                    "Créditos de PIS/Cofins e de CBS/IBS zerados: Real e Reforma ficam pessimistas.",
                    "Importe o Acompanhamento de Entradas.", "paginas/importar.py"),
        Verificacao("ICMS/ISS reais" if fora_simples else "Alíquotas de ICMS/ISS conferidas no cadastro",
                    icms_real if fora_simples else aliquotas_conferidas, 8,
                    "ICMS/ISS do Presumido e do Real estimados pelas alíquotas do cadastro.",
                    "Confira o ISS do município e o ICMS médio no Cadastro (ou importe as saídas com impostos).",
                    "paginas/cadastro.py"),
        Verificacao("RAT, FAP e Terceiros conferidos", not encargos_padrao, 6,
                    "Encargos sobre a folha (Presumido/Real) com valores padrão (RAT 2%, FAP 1, Terceiros 5,8%).",
                    "Informe o RAT do CNAE, o FAP do ano e o FPAS no Cadastro.", "paginas/cadastro.py"),
        Verificacao("Dados da Receita Federal consultados", bool(cliente.dados_receita), 6,
                    "Regime, CNAE e situação cadastral não confirmados.",
                    "No Cadastro, clique em Buscar na Receita.", "paginas/cadastro.py"),
        Verificacao("Sócios cadastrados", bool(cliente.socios), 8,
                    "Sem a carga sócio + empresa (Lei 15.270/2025), que pode mudar a recomendação.",
                    "Cadastre os sócios e a política de distribuição.", "paginas/socios.py"),
        Verificacao("Partilha do Simples para os anexos do cliente", not sem_partilha, 6,
                    f"Simples híbrido não calculado para o(s) Anexo(s) {', '.join(sem_partilha)}." if sem_partilha
                    else "", "Aguarda a tabela de partilha desses anexos (LC 214/2025) [CONFERIR].",
                    "paginas/configuracoes.py"),
        Verificacao("24 meses de histórico (sazonalidade)", n >= 24, 8,
                    "Projeção sem sazonalidade: meses fortes e fracos ficam na média.",
                    "Importe o histórico de dois anos completos.", "paginas/importar.py"),
    ]


def nota(verificacoes: list[Verificacao]) -> tuple[int, str]:
    total = sum(v.peso for v in verificacoes)
    feito = sum(v.peso for v in verificacoes if v.ok)
    n = round(100 * feito / total) if total else 0
    return n, ("Alta" if n >= 80 else "Média" if n >= 55 else "Baixa")
