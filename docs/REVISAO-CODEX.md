# Revisão crítica do motor — Codex

Revisão de 23/10/2026, sobre `main` em `e188e1b`, branch `codex/revisao-motor`.
Escopo: `calculo/`, `socios.py`, `projecao.py`, `equilibrio.py` e `regras/`.
Nenhum arquivo reservado ao outro agente foi alterado. Não foram versionados dados reais.
O checkout original não permitiu escrever em `.git`; o trabalho foi feito em clone local isolado,
a partir da referência `main` do repositório solicitado.

## Achados, em ordem de gravidade

As linhas indicam o código revisado nesta branch; a função identifica o ponto mesmo após mudanças de linha.
Não foi identificado achado CRÍTICO. Os quatro achados ALTO foram reproduzidos antes da correção.

| # | Gravidade (CRÍTICO/ALTO/MÉDIO/BAIXO) | Arquivo:linha | Problema | Cenário que falha (entrada → saída errada) | Correção proposta | Base legal (se for regra) |
|---|---|---|---|---|---|---|
| 1 | ALTO | `socios.py:103`, `visao_socios`; `regras/pessoa_fisica.py:86` | **Regra tributária:** alíquota efetiva PJ calculada sobre lucro depois do IRPJ/CSLL; superestima o redutor e pode subestimar o IRPFM. | Base sintética de 21 meses: Presumido apresenta 42,628356% em vez de 29,887715%. | **Corrigido:** recompor lucro antes dos tributos sobre renda em função de `regras/`. Teste `test_aliquota_pj_usa_lucro_antes_irpj_csll`. | Lei 9.250/1995, art. 16-B, §3º, I e III, incluído pela Lei 15.270/2025, art. 2º ([texto oficial](https://www2.camara.leg.br/legin/fed/lei/2025/lei-15270-26-novembro-2025-798354-publicacaooriginal-177117-pl.html)). |
| 2 | ALTO | `regras/pessoa_fisica.py:96`, `irpfm` | **Regra tributária:** usa alíquota nominal do IRPFM no redutor, em lugar da alíquota efetiva incremental dos dividendos. | Renda R$ 1,5 mi, dividendos R$ 1,2 mi, IR da tabela R$ 60 mil e PJ 30% → redutor R$ 72 mil e devido R$ 18 mil; corretos no modelo: R$ 42 mil e R$ 48 mil. | **Corrigido:** diferença entre imposto mínimo com e sem dividendos, antes do redutor, dividida pelos dividendos. Teste `test_redutor_usa_aliquota_incremental_pf`; memória do teste antigo corrigida com a lei. | Lei 9.250/1995, art. 16-B, §§2º e 3º, II, incluído pela Lei 15.270/2025, art. 2º (mesmo texto oficial). |
| 3 | ALTO | `projecao.py:46`, `_indice_sazonal` | **Código:** índice sazonal zero provoca divisão por zero e propaga NaN para todas as receitas projetadas. | Dois anos completos com janeiro sem receita, demais meses com R$ 100 mil, histórico até fev/2026 → seis meses projetados com NaN, interpretados como receita zero em somas. | **Corrigido:** usar índice neutro e emitir alerta quando qualquer fator sazonal for nulo/inválido. Teste `test_sazonalidade_sem_receita_em_um_mes`. | Não se aplica; tratamento numérico, sem alteração tributária. |
| 4 | ALTO | `equilibrio.py:98`, `_raizes` e `pontos_equilibrio.g` | **Código:** indisponibilidade de regime vira infinito, convertido em número finito; bissecção pode apresentar o limite de elegibilidade como ponto de igualdade. | Função −100 antes de 0,5 e +infinito depois → raiz falsa próxima de 0,5. NaN no meio da bissecção também era aceito. | **Corrigido:** comparação indisponível retorna NaN; rejeitar extremos e pontos intermediários não finitos. Teste `test_equilibrio_nao_confunde_indisponibilidade_com_raiz`. | Não se aplica; a elegibilidade tributária não foi alterada. |
| 5 | MÉDIO | `calculo/motor.py:41`, `Resultado.resumo` | **Código:** `all()` de recorte vazio retorna verdadeiro e permite recomendar um regime sem dados. | Pedir jan–jun/2040 em base encerrada em 2026 → regimes elegíveis e um marcado como melhor, todos com receita/tributos zero. | **Corrigido:** exigir recorte não vazio; teste `test_resumo_sem_meses_nao_recomenda_regime`. | Não se aplica. |
| 6 | MÉDIO | `calculo/real.py:85`, `calcular_real`; `socios.py:63`, `lucro_contabil` | **Limitação de dados:** basta existir custo/despesa em algum mês para assumir zero nos demais meses sem DRE. | Um mês com custos informados e outros com ambos ausentes → os meses ausentes entram com custo/despesa zero, sem distinguir ausência de gasto. | **Pendente:** definir política por competência (bloqueio, estimativa explícita ou alerta). Não inventar custos nem extrapolar DRE silenciosamente. | Não se propõe mudança de regra fiscal; qualidade dos dados de entrada. |
| 7 | MÉDIO | `socios.py:114`, `visao_socios` | **Premissa do modelo:** anualização da projeção pode misturar exercícios; distribuição mensal é uniforme, e a PJ do Simples é considerada zero para o redutor. | Projeção out/2026–mar/2027 → valores multiplicados por dois, sem apuração individual de cada exercício ou calendário real de pagamentos. | **Pendente [CONFERIR]:** separar exercício, rendas/deduções efetivas e cronograma de distribuição; incorporar partilha IRPJ/CSLL do DAS e validar regulamentação. Não se afirma que a projeção semestral substitui a apuração anual. | Lei 9.250/1995, arts. 6º-A, 16-A e 16-B, redação Lei 15.270/2025. |
| 8 | MÉDIO | `calculo/simples.py:109`, `fora`; `regras/simples.py` | **Regra a conferir:** sexta faixa e impedimento anual são tratados pela mesma condição; histórico parcial do ano anterior é anualizado para o sublimite. | Receita de apenas um mês do ano anterior de R$ 320 mil é extrapolada para R$ 3,84 mi e aciona impedimento no seguinte, sem informação sobre os outros meses. | **Pendente [CONFERIR]:** distinguir início de atividade, histórico ausente e excesso comprovado; conferir sexto intervalo e partilhas com o contador. A afirmação do briefing de que não havia tratamento da sexta faixa foi refutada: a condição existe. | LC 123/2006, arts. 13-A, 18 e 20; [Resolução CGSN 140/2018, art. 25](https://normas.receita.fazenda.gov.br/sijut2consulta/consulta/normas.fazenda.gov.br/sijut2consulta/link.action?idAto=92278&visao=original). Não alterados. |
| 9 | MÉDIO | `socios.py:168`, `otimizar_pro_labore` | **Premissa:** custo ótimo não inclui efeito sobre dividendos e compara com pró-labore atual elevado ao piso da grade. | Pró-labore atual abaixo do piso → `custo_atual` usa o piso; uma economia pode ser interpretada como relativa à retirada real. | **Pendente:** calcular referência real separada e explicitar objetivo parcial; preservar comparação histórica desta tarefa. | Não se propõe nova regra tributária. |
| 10 | BAIXO | `socios.py:78`, `visao_socios` | **Código:** período vazio causa divisão por zero; períodos fora da base distorcem anualização. | Sócio cadastrado e lista de meses vazia → `ZeroDivisionError`. | **Corrigido:** intersectar meses com a base e retornar visão vazia quando não houver meses. Teste `test_socios_sem_meses_nao_divide_por_zero`. | Não se aplica. |

## Foto e isolamento das mudanças

`tests/foto_motor.json` foi capturado pelo processo que carregou o motor original, antes das
alterações, e registrado no commit `4436baa`. São 12 casos: fixture de 21 meses do `conftest`,
as nove bases literais de `test_calculo`, a base com prejuízo e uma variante com sócio sintético.
Cada caso contém `calcular` e `gerar_planejamento` completo, com histórico, bases e resultados
dos três cenários, resumos, equilíbrio, curva, transição, alertas e visão de sócios.
Somente o horário de geração e os prazos dependentes do dia corrente ficam fora da foto.

O teste usa tolerância absoluta de R$ 0,01 e tolerância relativa zero. Estruturas, textos,
elegibilidade, valores ausentes e recomendações também são comparados.
A primeira rodada de otimização passou nos 12 casos sem exceções.
A foto original **não foi regravada** após as correções: a única exceção esperada na foto
é a coluna `aliquota_pj` das linhas Presumido e Real do caso com sócio, ajustada explicitamente
por `a / (1 + a)` conforme o achado 1. Nesse caso não há mudança monetária do redutor.
O achado 2 possui reprodução separada de R$ 30 mil de diferença, com memória legal acima.

## Otimização

- Rateios por trimestre/ano e acessos nos laços passaram a usar arrays NumPy.
- Receita, tributos locais, encargos e vetores são reaproveitados apenas no contexto privado
  de uma chamada a `calcular`. Não há cache global de clientes, bases ou resultados.
- O híbrido só é montado quando solicitado e disponível.
- A apuração de IRPJ/CSLL e compensações do Real foi extraída para `apurar_lucro`, usada tanto
  pelo motor completo quanto pela sensibilidade de margem. Os períodos históricos continuam
  sendo percorridos, inclusive no modo anual e com saldos fiscais iniciais distintos.
- A busca de equilíbrio guarda apenas resultados da própria chamada; a curva de margem
  reaproveita tributos invariantes. Não se reduziu a grade nem a precisão da bissecção.
- `test_avaliador_margem_bate_motor_com_prejuizos` confere o caminho reaproveitado contra
  o motor completo, com lucro/prejuízo, períodos anual/trimestral e saldos iniciais.

## Medições e validação

Ambiente: Windows 10 (19045), Python 3.13.5, pandas 3.1.0 e NumPy 2.5.4.
Tempos de parede em segundos, sem perfilador:

| Operação | Antes (mediana) | Depois (mediana) | Meta |
|---|---:|---:|---:|
| `calcular`, 21 meses | 1,293366 | 0,089684 | < 0,1 |
| `gerar_planejamento`, completo | 44,955713 | 4,085861 | < 8 |

Amostras antes: motor `[1,293366; 1,419088; 2,536958; 1,059214; 0,916810]`;
planejamento `[44,955713; 44,777746; 96,914110]`.
Amostras depois: motor `[0,134513; 0,085401; 0,090826; 0,095751; 0,089684]`;
planejamento `[5,809818; 5,856074; 4,217771]`.
As metas foram atingidas em **todas as amostras da medição final**, executada após o fim
da suíte, sem testes concorrentes. O ambiente apresentou variação significativa de tempo
(inclusive antes da mudança); medições intermediárias tiveram chamadas acima de 0,1 s.
Os tempos registrados são amostras locais, não uma garantia de latência em qualquer máquina.

A execução integral sem isolamento do kit visual produziu **64 aprovados, 2 pulados e 2 falhas**
em 138,97 s. As falhas ocorreram em relatório e página de relatórios ao consultar
`G:\Meu Drive\ZERA - IDENTIDADE VISUAL` (acesso negado no processo do Codex).
Foi adicionado o plugin **optativo** `tests/ambiente_sintetico.py`, que desativa somente a
busca automática do kit em pastas externas durante os testes; PDF e páginas continuam
sendo executados. Não se alterou nem se pulou código de produção para ocultar essas falhas.
A execução integral isolada terminou com **67 aprovados, 2 pulados e nenhuma falha**, em 142,34 s.
Todos os 12 casos da foto e os testes de reprodução e equivalência passaram.

Comando de validação neste ambiente PowerShell:

```powershell
$env:PYTHONPATH = 'src;tests'
python -m pytest -p ambiente_sintetico -p no:cacheprovider --basetemp=../tmp-suite-isolada
```

O diretório temporário explícito evita outro acesso negado no diretório padrão do pytest.
As duas regressões da CS Geartech são puladas porque os arquivos de amostra não estão
presentes. Antes de integrar, executar essas regressões onde existirem as amostras, confirmando
Presumido R$ 284.704,68, Simples R$ 237.945,88 e Real R$ 574.294,06. A otimização não deve
alterar esses tributos da PJ; as correções legais afetam o redutor na visão de sócios.

Reprodução: definir `PYTHONPATH=src` e executar `python tests/medir_motor.py`.
O script usa a base sintética de 21 meses, um aquecimento do motor, cinco medições de
`calcular` e três planejamentos completos (equilíbrio, curva e transição ligados).
As medições originais foram repetidas a partir de `git archive e188e1b`, no mesmo Python.
Não são limites de tempo impostos ao pytest, para não criar falhas aleatórias de CI.

## Limites da revisão

As pendências dos achados 6–9 não foram corrigidas. Tabelas de partilha do Simples não foram
certificadas linha a linha; o cálculo híbrido sobre o DAS cheio não foi modificado sem evidência
legal de erro. A tendência forte já gera alerta, portanto não foi arbitrariamente limitada.
Tabelas de pessoa física permanecem referenciadas em 2026. Não foi feita uma auditoria fiscal
completa de todas as vigências, municípios e hipóteses de transição. As correções do redutor
não substituem demonstrações financeiras, ajuste anual ou regulamentação aplicável.
Não houve alteração em `app/`, `dominio/`, `consulta_cnpj.py`, `relatorio/`, `README.md`,
`PROMPT.md` ou `CHANGELOG.md`.
