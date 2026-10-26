# Manual da equipe — Zera Planejamento Tributário

## 1. Abrir o sistema
- O sistema abre na **Mesa do escritório**: números da carteira, agenda de decisões e um cartão por cliente com o
  progresso do roteiro. Clique em **Abrir dashboard** no cartão para ir direto ao cliente.
- Na barra lateral, o **Roteiro do cliente** mostra o que já foi feito e o próximo passo; clique em cada item para ir
  direto à tela.
- Dois cliques em **Iniciar Zera Planejamento.bat**. Abre uma janela preta e, em seguida, o navegador. Mantenha a janela preta aberta enquanto usa.
- Primeira vez no computador: rode antes o **instalar.bat**.

## 2. Cadastrar o cliente (página **Cadastro**)

**Atalho:** digite o CNPJ em *Buscar dados na Receita Federal* e clique em **Buscar na Receita**. O sistema preenche
razão social, município, UF, atividade (CNAE) e sugere o regime atual (Simples ou a última tributação declarada).
Pode também cadastrar os sócios do quadro societário. Confira tudo e clique em **Salvar cadastro**; as alíquotas
abaixo (ISS, RAT, FAP, Terceiros) continuam sendo do escritório.

| Campo | Onde conferir | Por que importa |
|---|---|---|
| Regime atual | Domínio / opção do ano | No Simples, ICMS e ISS do Presumido/Real são estimados pelas alíquotas do cadastro |
| Anexo das notas de serviço | CNAE e Fator R | III, IV, V ou "Fator R" (III ou V pela folha) |
| ISS do município | Lista de serviços do município | Entra no Presumido/Real |
| RAT, FAP, Terceiros | CNAE preponderante, FAP do ano, FPAS | Encargos fora do Simples |
| Prejuízo fiscal / base negativa | Parte B do LALUR | Lucro Real |
| CBS/IBS de referência | Resolução do Senado (até 15/12/2026) | Simulações de 2027 em diante |

## 3. Exportar do Domínio
Exporte **em Excel**, do mesmo período. O ideal é de janeiro do ano anterior até o último mês fechado.

- **Escrita Fiscal:**
  - Acompanhamento de Serviços (e de Saídas, se o cliente vende mercadoria);
  - Acompanhamento de Entradas.
- **Folha:** Extrato Mensal, cálculo "Folha Mensal e Complementar".
- **Contabilidade:** D.R.E. Melhor uma por mês. Com uma única DRE acumulada, os custos são divididos igualmente entre os meses e o sistema avisa.

O nome dos arquivos não importa: o sistema reconhece cada relatório pelo título.

## 4. Importar (página **Importar Domínio**)
1. Envie todos os arquivos de uma vez e clique em **Ler relatórios**.
2. Leia os **alertas**:
   - **CRÍTICO:** não grava. Exemplos: CNPJ de outra empresa, relatório lido incompleto.
   - **ATENÇÃO:** revisar. Exemplos: DRE acumulada, conta genérica alta, prestador que já foi empregado, CFOP sem regra.
   - **INFO:** registro. Exemplos: imobilizado, remessas para conserto ignoradas, DIFAL.
3. Confira as **conferências cruzadas** (receita das notas × DRE; folha × DRE) e o que será gravado.
4. Clique em **Gravar na base do cliente**.

Só os meses do período de cada relatório são regravados. Os originais e a conferência ficam guardados na pasta do cliente.

## 4.1 Outros documentos (página **Outros documentos**)
Para qualquer planilha (Excel, CSV) ou PDF com texto — DRE, balancete, faturamento, folha, extrato do PGDAS-D:
1. Envie o arquivo. O sistema escolhe a tabela com mais valores (troque se precisar) e mostra onde achou os meses.
2. Documento de um mês só: informe a competência. Valores acumulados no ano: marque a opção.
3. Na tabela **"Vai para"**, ligue cada linha a um item da base. Totais, subtotais e lucro ficam em **Ignorar**.
4. Confira a prévia e clique em **Gravar na base do cliente**. As escolhas ficam salvas: no próximo documento do mesmo
   cliente, os mesmos rótulos já vêm ligados.

PDF digitalizado (foto/escaneado) não tem texto: peça o arquivo original ou em Excel.

## 5. Completar a base (página **Base mensal**)
Itens que não vêm do Domínio:

- **Aluguel de PJ** (base de crédito);
- **meses anteriores** sem relatório (use "Incluir meses" e digite receita e folha);
- **adições/exclusões do LALUR**.

Também dá para baixar a base em Excel, preencher e enviar de volta.

## 6. Dashboard (tela inicial)
- **Faixa preta:** a recomendação — mudar ou manter o regime, a economia por ano e até quando decidir.
- **Cartões:** menor carga, economia, carga efetiva, receita, Fator R e próximo prazo.
- **Filtros:** cenário (Neutro, Otimista, Pessimista), período (próximos meses ou últimos 12) e regimes nos gráficos.
- **Gráficos:** passe o mouse para ver os valores; clique num item da legenda para destacá-lo.

## 6.1 Ler o planejamento em detalhe (página **Planejamento**)
- **Menor carga:** regime e economia sobre o segundo colocado no cenário Neutro. Com vantagem menor que 3%, o sistema avisa que qualquer premissa pode inverter a ordem.
- **Cenários:** o mesmo para Otimista (+15%) e Pessimista (−15%).
- **Pontos de equilíbrio:** margem em que o Lucro Real passa a valer a pena, faturamento em que Simples e Presumido se igualam, folha necessária para o Fator R.
- **Transição 2026–2033:** os mesmos 12 meses sob a regra de cada ano.

## 6.1.1 Comparação entre anos (página **Comparação entre anos**)
- **Mesmo período:** compara os meses já fechados deste ano com os mesmos meses do ano anterior (ex.: jan–set).
- **Por ano:** realizado dos anos anteriores, o ano atual com os meses que faltam estimados e o próximo ano projetado.
- **Base da projeção:** tendência, média ou média + crescimento (vazio = usa o crescimento observado).
- **Cenários do próximo ano:** pessimista, central e otimista; a faixa preta mostra o regime de menor carga e a
  economia estimada — a decisão de regime é feita em janeiro.
- Anos sem DRE não mostram o Lucro Real: importe a DRE para comparar.

## 6.1.3 Reforma Tributária 2026–2033
Mostra quanto o cliente pagaria em cada regime de 2026 a 2033 com os números atuais, a composição de cada ano
(PIS/Cofins → CBS; ICMS/ISS → IBS) e o cronograma da transição. Ajuste a CBS/IBS de referência e o regime
diferenciado (reduções de 30% ou 60%) para ver a sensibilidade; **Salvar estas premissas** grava no cadastro.

## 6.1.4 Precisão da análise (no Dashboard)
Nota de 0 a 100 dizendo o quanto os dados sustentam os números, com os pontos a melhorar em ordem de impacto e o
atalho para resolver cada um. Antes de levar ao cliente, mire em precisão **alta**.

## 6.1.2 Simulador "E se…"
Mexa nos controles de receita, folha, custos e pró-labore: o sistema recalcula na hora quanto cada regime pagaria nos
próximos 12 meses e avisa se o regime mais barato muda. Use na reunião com o cliente; **Voltar ao cenário base**
desfaz tudo.

## 6.2 Sócios e pró-labore
- Cadastre cada sócio (participação, pró-labore, dependentes, outras rendas) e quanto do lucro é distribuído.
- A tabela mostra empresa + sócios por regime (Lei 15.270/2025: lucros acima de R$ 50 mil/mês e imposto mínimo).
- **Calcular pró-labore ótimo** mostra o pró-labore de menor custo e quanto falta para o Fator R chegar a 28%.

## 7. Relatórios (página **Relatórios**)
- **Parecer ao cliente (Word + PDF):** uma página em linguagem simples com a recomendação, os valores por ano e o
  prazo. Revise no Word e envie o PDF.
- **Excel:** resumo, uma aba por regime com memória mês a mês, base, origem dos dados, projeções, transição, premissas e alertas.
- **PDF:** técnico, com o timbrado da Zera (configure o kit em **Configurações**).

Revise antes de enviar ao cliente.

## 8. Ajustar a classificação (página **De-Para**)
Regras do cliente valem antes das padrão. Exemplos:

| Tipo | Chave | Destino | Uso |
|---|---|---|---|
| `CFOP_ENTRADA` | `2556` | `cred_insumos` | Uniformes/EPI de empresa de manutenção (Lei 10.833/03, art. 3º, X) |
| `FORNECEDOR` | `ROLAMENTOS` | `cred_insumos` | Um fornecedor de peças |
| `DRE_CONTA` | `4.2.1.06.000008` | `despesa_indedutivel` | Conta que precisa ser adicionada no LALUR |

Depois de salvar, importe os relatórios de novo.

## 9. Painel da carteira (novembro/dezembro)
Clique em **Analisar a carteira**: todos os clientes em MUDAR, AVALIAR ou MANTER, com economia anual estimada e o
prazo de decisão. Abra o dashboard de cada cliente em MUDAR antes de recomendar.

## Problemas comuns

| Mensagem | O que fazer |
|---|---|
| "Python não encontrado" | Reinstale o Python marcando "Add python.exe to PATH" |
| "Não reconheci o relatório" | Exportou outro relatório ou em PDF; exporte em Excel |
| CRÍTICO "soma lida ≠ Total Geral" | O layout do Domínio mudou: avise quem mantém o sistema |
| PDF sem timbrado | Configure a pasta "ZERA - IDENTIDADE VISUAL" em Configurações |
