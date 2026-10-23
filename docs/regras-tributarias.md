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
| Sublimite | receita do ano anterior > R$ 3,6 mi → impedida o ano todo; acumulada no ano > R$ 4,32 mi → a partir do mês seguinte. Impedida: DAS sem a parcela de ICMS/ISS (`regras/dados/simples_partilha_icms_iss.csv`) e ICMS/ISS apurados fora. RBT12 na 6ª faixa: ICMS/ISS fora `[CONFERIR Res. CGSN 140, art. 25]` | art. 13-A; art. 20, §§ 1º e 1º-A |
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

## Sócio pessoa física — pró-labore e lucros (2026)
| Regra | Implementação | Base |
|---|---|---|
| INSS do sócio | 11% do pró-labore até o teto (R$ 8.475,55) | Lei 8.212/91, art. 21 e 30, § 4º; Lei 10.666/03, art. 4º |
| IRRF do pró-labore | tabela mensal; deduz INSS + dependentes (R$ 189,59) ou o simplificado (R$ 607,20) | Lei 15.191/2025 |
| Redução do IR | até R$ 5.000/mês: até R$ 312,89 (IR zero); até R$ 7.350: 978,62 − 0,133145 × rendimento | Lei 15.270/2025 |
| IRRF sobre lucros | 10% sobre o total pago no mês se a mesma PJ pagar mais de R$ 50 mil à mesma PF (antecipação) | Lei 15.270/2025 |
| IRPFM | renda anual > R$ 600 mil: (renda ÷ 60.000 − 10)%, 10% a partir de R$ 1,2 mi; deduz IR da tabela e o redutor (PJ + PF até 34%) `[CONFERIR]` | Lei 15.270/2025 |
| Lucro distribuível | lucro contábil depois dos tributos do regime (CBS/IBS por fora não reduzem) × fração distribuída | (premissa do cadastro) |
| Simples | alíquota efetiva da PJ para o redutor = 0% `[CONFERIR]`; retenção sobre lucros do Simples com divergência | — |

## Prazos de decisão
Opção pelo Simples e exclusão por opção até o último dia útil de janeiro (LC 123, art. 16, § 2º, e art. 30, § 1º, I);
Presumido com a 1ª quota do IRPJ do 1º trimestre (último dia útil de abril; Lei 9.430/96, art. 26, § 1º); Real anual com
a estimativa de janeiro; opção semestral do Simples pelo IBS/CBS por fora em abril e setembro `[CONFERIR]` (LC 214/2025,
art. 41). Dias úteis sem feriados nacionais (fixos e Sexta-feira Santa).

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
- IRPFM de sócios de seguradoras e instituições financeiras (limites de 40% e 45%) e rendimentos isentos da base do IRPFM.
