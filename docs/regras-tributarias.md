# Regras tributárias implementadas

Fonte de verdade: o código em `src/zera_planejamento/regras/` e `calculo/`. Este documento resume com a base legal. Itens `[CONFERIR]` aparecem também na tela e no PDF.

## Simples Nacional — LC 123/2006
| Regra | Implementação | Base |
|---|---|---|
| Alíquota efetiva | (RBT12 × nominal − parcela a deduzir) ÷ RBT12, Anexos I–V | art. 18, § 1º-A |
| RBT12/FS12 até 12/2026 | 12 meses anteriores ao PA | art. 18, § 1º |
| RBT12/FS12 desde 01/2027 | 12 meses antecedentes ao mês anterior ao PA | art. 18 com redação da LC 214/2025 |
| Início de atividade / histórico curto | média dos meses disponíveis × 12 | Res. CGSN 140/2018, art. 22 |
| Fator R | FS12 ÷ RBT12 ≥ 28% → Anexo III; senão V. FS12 = salários + pró-labore + FGTS (+ CPP do DAS, opção `[CONFERIR]`) | art. 18, §§ 5º-J, 5º-M e 24 |
| Sublimite | RBT12 > R$ 3,6 mi → ICMS/ISS fora do DAS `[CONFERIR: simplificado]` | art. 13-A |
| Exclusão | receita do ano > R$ 4,8 mi → a partir de janeiro seguinte; > R$ 5,76 mi → mês seguinte | art. 3º, §§ 9º e 9º-A |
| Anexo IV | CPP (20% + RAT × FAP) fora do DAS | art. 13, § 3º; art. 18, § 5º-C |
| Partilha com CBS/IBS (2027+) | `regras/dados/simples_partilha_reforma.csv` — Anexos I e III `[CONFERIR]` | LC 214/2025 |
| Híbrido (2027+) | DAS sem a parcela CBS/IBS + CBS/IBS não cumulativos por fora | LC 214/2025; opção semestral (Res. CGSN) |

## Lucro Presumido
| Regra | Implementação | Base |
|---|---|---|
| Presunção | por anexo: comércio/indústria 8%/12%, serviços 32%/32% (editável no cadastro) | Lei 9.249/95, art. 15 e 20 |
| Acréscimo LC 224/2025 | +10% no percentual sobre a receita acima de R$ 1,25 mi no trimestre, saldo aproveitado, ajuste no 4º tri ao limite anual de R$ 5 mi; IRPJ desde 01/2026, CSLL desde 04/2026 `[questionamento judicial]` | LC 224/2025, art. 4º; IN RFB 2.305/2025 e 2.306/2026 |
| IRPJ/CSLL | trimestrais; IRPJ 15% + 10% acima de R$ 20 mil × meses; CSLL 9%; receitas financeiras somam à base | Lei 9.430/96, art. 1º, 3º, 25 |
| PIS/Cofins até 2026 | 0,65% + 3% cumulativos, sem ICMS na base | Lei 9.718/98; Tema 69/STF |

## Lucro Real
| Regra | Implementação | Base |
|---|---|---|
| PIS/Cofins até 2026 | 1,65% + 7,6% sobre a receita sem ICMS − crédito sobre aquisições sem ICMS; saldo credor transportado | Leis 10.637/02 e 10.833/03; Lei 14.592/23 |
| Receitas financeiras | PIS 0,65% + Cofins 4% | Decreto 8.426/2015 |
| Lucro | receita + rec. financeiras − custos − despesas − folha − FGTS − encargos − PIS/Cofins − ICMS − ISS + adições − exclusões | RIR/2018 |
| Compensação | prejuízo/base negativa até 30% do lucro do período, também entre trimestres | Lei 8.981/95, art. 42; Lei 9.065/95, art. 15 |
| Sem DRE | lucro anual estimado do cadastro × participação da receita | (aproximação) |

## Encargos sobre a folha (Presumido e Real)
INSS patronal 20% sobre salários e pró-labore; RAT × FAP e Terceiros só sobre salários (Lei 8.212/91, art. 22).

## Reforma Tributária — EC 132/2023 e LC 214/2025

| Ano | PIS/Cofins | CBS | IBS | ICMS/ISS |
|---|---|---|---|---|
| 2026 | vigentes | 0,9% teste (sem custo) | 0,1% teste (sem custo) | integrais |
| 2027–2028 | extintos | referência − 0,1 p.p. | 0,1% | integrais |
| 2029 | | referência | 10% da referência | 90% |
| 2030 | | | 20% | 80% |
| 2031 | | | 30% | 70% |
| 2032 | | | 40% | 60% |
| 2033 | | | 100% | extintos |

- Referências **editáveis** `[CONFERIR]`: CBS 9,21% e IBS 18,7% (estimativas do CGIBS); o Senado fixa a de 2027 até 15/12/2026.
- CBS/IBS por fora: não entram na receita, na base presumida nem no lucro. Até 2032, ICMS e ISS ficam fora da base da CBS/IBS (LC 214, art. 12, § 2º).
- Crédito amplo (art. 47): insumos, energia, aluguel, serviços, fretes, uso e consumo e imobilizado (opção).
- Premissa de preço: o valor da operação sem tributos é mantido e a CBS/IBS é cobrada por fora.

## Fora do modelo
- ICMS-ST, monofásicos e exportação no PGDAS-D;
- IPI e Imposto Seletivo;
- benefícios estaduais e municipais;
- ISS fixo de sociedade uniprofissional;
- desoneração da folha;
- JCP e incentivos do Lucro Real;
- crédito de PIS/Cofins sobre depreciação;
- Lei 15.270/2025 (dividendos e IR mínimo da pessoa física) — previsto no roadmap.
