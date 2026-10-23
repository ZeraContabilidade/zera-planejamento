# Manual da equipe — Zera Planejamento Tributário

## 1. Abrir o sistema
- Dois cliques em **Iniciar Zera Planejamento.bat**. Abre uma janela preta e, em seguida, o navegador. Mantenha a janela preta aberta enquanto usa.
- Primeira vez no computador: rode antes o **instalar.bat**.

## 2. Cadastrar o cliente (página **Cadastro**)

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

## 5. Completar a base (página **Base mensal**)
Itens que não vêm do Domínio:

- **Aluguel de PJ** (base de crédito);
- **meses anteriores** sem relatório (use "Incluir meses" e digite receita e folha);
- **adições/exclusões do LALUR**.

Também dá para baixar a base em Excel, preencher e enviar de volta.

## 6. Ler o planejamento (página **Planejamento**)
- **Menor carga:** regime e economia sobre o segundo colocado no cenário Neutro. Com vantagem menor que 3%, o sistema avisa que qualquer premissa pode inverter a ordem.
- **Cenários:** o mesmo para Otimista (+15%) e Pessimista (−15%).
- **Pontos de equilíbrio:** margem em que o Lucro Real passa a valer a pena, faturamento em que Simples e Presumido se igualam, folha necessária para o Fator R.
- **Transição 2026–2033:** os mesmos 12 meses sob a regra de cada ano.

## 7. Relatórios (página **Relatórios**)
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

## Problemas comuns

| Mensagem | O que fazer |
|---|---|
| "Python não encontrado" | Reinstale o Python marcando "Add python.exe to PATH" |
| "Não reconheci o relatório" | Exportou outro relatório ou em PDF; exporte em Excel |
| CRÍTICO "soma lida ≠ Total Geral" | O layout do Domínio mudou: avise quem mantém o sistema |
| PDF sem timbrado | Configure a pasta "ZERA - IDENTIDADE VISUAL" em Configurações |
