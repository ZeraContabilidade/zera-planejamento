# PROMPT — Sistema de Planejamento Tributário Zera

> Especificação viva do sistema, para usar com o Claude Code na raiz deste repositório.
> Para começar uma sessão: *"Leia o PROMPT.md e o CLAUDE.md e me diga o estado do projeto antes de mexer em qualquer coisa."*

---

## 1. Quem somos e para que serve

A **Zera Contabilidade** é um escritório de contabilidade em São Paulo. Usamos o **Sistema Domínio** (Escrita Fiscal, Contabilidade e Folha), e a maioria dos clientes está no Simples Nacional ou no Lucro Presumido.

O sistema faz **planejamento tributário mensal com projeção semestral**:

1. **Lê os relatórios exportados do Domínio**, sem digitação: serviços, saídas, entradas, extrato da folha e DRE.
2. **Monta a base mensal** do cliente: receita por anexo, base de crédito, folha, custos, despesas e resultado.
3. **Calcula mês a mês** Simples Nacional, Simples híbrido (IBS/CBS por fora), Lucro Presumido e Lucro Real, com as regras de 2026 e a transição da Reforma até 2033.
4. **Projeta os próximos 6 meses** em três cenários: Neutro (tendência), Otimista (+15%) e Pessimista (−15%).
5. **Mostra o regime de menor carga** (R$ e %), os **pontos de equilíbrio** e os **riscos encontrados nos dados**.
6. **Entrega** um Excel auditável (com gráficos nativos) e um PDF técnico com a identidade da Zera.

**Quem usa:** a equipe, que não programa, no Windows, pela **tela no navegador**.

**Natureza do resultado:** é **rascunho técnico para o contador revisar** antes de ir ao cliente. O sistema não decide sozinho nem promete resultado fiscal.

---

## 2. Decisões já tomadas

| Tema | Decisão |
|---|---|
| Cálculo | **Motor único em Python** (`src/zera_planejamento/calculo`). O Excel gerado é saída auditável, não calcula. O motor Excel antigo da Zera fica só como referência histórica. |
| Interface | **Streamlit** (tela no navegador, local). Também há linha de comando para uso em lote. |
| Dados de clientes | Fora do git, em `C:\ZeraPlanejamento\dados` (variável `ZERA_DADOS`). Um JSON de cadastro e um CSV de base por cliente. |
| Leitura do Domínio | `python-calamine` lê o .xls do Domínio direto (o `xlrd` recusa). Colunas localizadas por rótulo, não por posição. |
| Regras | Em código + `regras/dados/*.csv`, com base legal e `[CONFERIR]` quando dependem de ato não publicado. |
| Identidade visual | Kit "ZERA - IDENTIDADE VISUAL" (timbrado, Cormorant Garamond, Inter, preto `#111111` e dourado `#C5A15F`). No app: tema em `app/.streamlit/config.toml`, logo e fontes em `app/static/`; PDF usa o kit configurado na tela. |

---

## 3. Estado atual — v0.3.0

```
src/zera_planejamento/
  regras/        simples.py (anexos, RBT12 2026 × 2027, sublimite), federais.py (Presumido/LC 224, Real), reforma.py (CBS/IBS 2026–2033)
                 pessoa_fisica.py (INSS/IRRF 2026, Lei 15.270: dividendos e IRPFM)
                 dados/simples_partilha_reforma.csv (partilha do DAS com CBS/IBS — Anexos I e III)
                 dados/simples_partilha_icms_iss.csv (ICMS/ISS no DAS por anexo e faixa — sublimite)
  base.py        base mensal canônica (colunas, origem de cada valor, CSV, planilha de digitação)
  cliente.py     cadastro e pastas; configuracoes.py (kit visual, assinatura)
  dominio/       leitura.py, relatorios.py (Serviços, Saídas, Entradas, Extrato Mensal, DRE), depara.py, importar.py
  calculo/       comum.py, simples.py (por dentro + híbrido), presumido.py, real.py, motor.py (+ simular_transicao)
  projecao.py    3 cenários; equilibrio.py (break-even e curva); planejamento.py (fluxo completo)
  socios.py      sócio + empresa (Lei 15.270) e otimizador de pró-labore / Fator R
  prazos.py      calendário de decisões (dias úteis); carteira.py (painel de todos os clientes)
  relatorio/     graficos.py (PNG), excel.py (gráficos nativos), pdf.py (ReportLab, timbrado)
  painel.py      dados do dashboard (recorte por cenário e período, indicadores)
  app/           main.py, visual.py (identidade Zera), .streamlit/config.toml (tema), static/ (logo e fontes)
                 paginas/ (dashboard, cadastro, importar, base, planejamento, socios, relatorios, carteira, depara, configuracoes)
  cli.py         zera-planejamento app | clientes | importar | relatorio | carteira
tests/           40 testes: cálculo com memória, pessoa física, sublimite, sócios, prazos, carteira, leitores, fluxo, app e regressão CS Geartech
```

**Regressão real (CS Geartech, jan–set/2026, `amostras/` fora do git):**
- **Presumido:** bate no centavo com o motor Excel (R$ 284.704,68).
- **Simples:** R$ 237.945,88. A diferença para o Excel é explicada: o Excel aplicava a RBT12 de 2027 aos meses de 2026.
- **Real:** R$ 574.294,06. O motor antigo dava crédito de PIS/Cofins sobre uso e consumo e sobre um aluguel sem conta na DRE.

---

## 4. Regras implementadas (resumo — detalhes em `docs/regras-tributarias.md`)

**Simples Nacional** (LC 123/2006)
- Anexos I–V e Fator R (28%).
- **RBT12/FS12:** 12 meses anteriores até dez/2026; a partir de jan/2027, os 12 meses antecedentes ao **mês anterior** (LC 214/2025).
- Sublimite de R$ 3,6 mi exato: receita do ano anterior ou acumulada no ano (excesso acima de 20% → mês seguinte); DAS sem a parcela de ICMS/ISS.
- Exclusão pela receita do ano (4,8 mi; excesso acima de 20% exclui no mês seguinte).
- Anexo IV com CPP fora do DAS.
- **Híbrido a partir de 2027:** DAS sem a parcela de CBS/IBS + CBS/IBS não cumulativos por fora.

**Lucro Presumido**
- Presunção por anexo.
- **LC 224/2025:** +10% na presunção acima de R$ 1,25 mi por trimestre, com ajuste anual a R$ 5 mi (IN RFB 2.306/2026). IRPJ desde 01/2026; CSLL desde 04/2026.
- IRPJ/CSLL trimestrais, com receitas financeiras na base.
- PIS/Cofins cumulativos até 2026, sem ICMS na base (Tema 69); CBS/IBS a partir de 2027.

**Lucro Real**
- PIS/Cofins não cumulativos até 2026, com crédito sem ICMS (Lei 14.592/2023); receitas financeiras a 4,65%.
- Lucro = DRE − folha − encargos − tributos sobre a receita (CBS/IBS são por fora).
- Trimestral ou anual, com compensação de prejuízo limitada a 30%, inclusive entre trimestres.

**Encargos**
- 20% sobre salários e pró-labore.
- RAT × FAP e Terceiros só sobre salários.

**Sócio pessoa física (Lei 15.270/2025)**
- INSS 11% do pró-labore até o teto; IRRF 2026 (Lei 15.191/2025) com a redução até R$ 7.350/mês.
- Lucros acima de R$ 50 mil/mês por sócio e por empresa: IRRF de 10% sobre o total (antecipação).
- IRPFM: renda anual acima de R$ 600 mil, até 10% a partir de R$ 1,2 mi, com redutor PJ + PF até 34%.

**Prazos de decisão**
- Opção/exclusão do Simples (último dia útil de janeiro), Presumido (1ª quota do IRPJ, abril), Real anual (estimativa de janeiro), opção semestral do híbrido, alíquota da CBS.

**Reforma**

| Período | CBS | IBS | ICMS/ISS |
|---|---|---|---|
| 2026 | 0,9% de teste, sem custo | 0,1% de teste, sem custo | integrais |
| 2027–2028 | referência − 0,1 p.p. | 0,1% | integrais |
| 2029–2032 | referência | 10% a 40% da referência | reduzidos de 10% a 40% |
| 2033 | referência | pleno | extintos |

- Crédito amplo de CBS/IBS (inclui uso e consumo e imobilizado).
- CBS e IBS ficam sem ICMS/ISS na base até 2032.

**Pendências `[CONFERIR]`** (aparecem na tela e no PDF):
- alíquota de referência da CBS (o Senado fixa até 15/12/2026; padrão 9,21%) e do IBS (18,7%);
- partilha do Simples dos Anexos II, IV e V;
- LC 224/2025 sob questionamento judicial;
- inclusão da CPP do DAS no Fator R;
- RBT12 na 6ª faixa sem impedimento pelo sublimite (Res. CGSN 140, art. 25);
- Lei 15.270: redutor do IRPFM, restituição do IRRF excedente e alíquota da PJ no Simples;
- tabelas da pessoa física de 2026 e prazos de opção do Simples híbrido.

---

## 5. Como trabalhar neste projeto

- **Português, direto, como contador experiente.** Primeiro a resposta, depois o porquê.
- **Regra tributária nova ou alterada:**
  - mostrar a base legal (lei, artigo, IN);
  - pesquisar se houver dúvida de vigência; 2026 e 2027 têm muitas mudanças (Reforma, LC 224/2025, Lei 15.270/2025);
  - na dúvida, marcar `[CONFERIR]` e incluir em `regras.pendencias_conferir()`;
  - nunca inventar alíquota, prazo ou caminho de menu do Domínio.
- **Todo cálculo tem teste com memória de cálculo nos comentários.** A regressão da CS Geartech precisa continuar passando, ou a diferença precisa ser explicada no PR.
- **Dados de cliente nunca entram no git.** Testes de leitura usam relatórios sintéticos no layout do Domínio (`tests/conftest.py`).
- **Antes de mudanças grandes** (arquitetura, formato da base, De-Para padrão), perguntar uma vez, de forma curta.
- **Ao fim de cada tarefa:** o que mudou, como testou e o próximo passo.

---

## 6. Sugestões e melhorias (roadmap priorizado)

Cada item traz o critério de aceite. Os itens **P1** têm o maior ganho para o escritório.

### P1 — Precisão e confiança no número

1. **Conferência "DAS calculado × DAS pago".** Importar o extrato do PGDAS-D (PDF ou relatório do Domínio) e comparar mês a mês com o DAS que o motor calcula. É a melhor prova de que a base e as regras estão certas.
   *Aceite:* diferença por mês na tela e no PDF; alerta acima de 1%.
2. **DRE mensal sem esforço.** Aceitar o **balancete mensal** ou várias DREs acumuladas (uma por fim de mês, o motor já faz a diferença) e orientar a exportação. Com isso some a divisão igual dos custos entre os meses, que distorce o Lucro Real trimestral.
   *Aceite:* importar 9 DREs acumuladas gera custos mês a mês exatos.
3. **Histórico de 12 meses anteriores automático.** Aceitar relatórios do ano anterior ou o extrato do PGDAS-D para preencher a RBT12/FS12, sem digitar.
   *Aceite:* sem alerta de "RBT12 proporcionalizada" quando há 13+ meses.
4. **Saldos do LALUR.** Importar a Parte B (prejuízo fiscal e base negativa) e as adições/exclusões recorrentes da ECF anterior.

### P1 — Decisão do cliente

5. **Parecer ao cliente em Word + PDF** com o timbrado da Zera (skill `identidade-visual-zera`, `zera_doc.js`), em 1–2 páginas de linguagem simples: o que muda, quanto custa, o que recomendamos e até quando decidir. O PDF técnico continua sendo o documento interno.
6. ✅ *(v0.2.0)* **Lei 15.270/2025 — visão sócio + empresa.** Somar à carga da PJ a retenção de 10% sobre dividendos acima de R$ 50 mil/mês por sócio e o IR mínimo da pessoa física. Cadastrar sócios, percentual de distribuição e pró-labore. Pode inverter a recomendação para quem distribui muito lucro.
7. **Simples híbrido de verdade.** Partilha dos Anexos II, IV e V; percentual da receita vendida para PJ (que aproveita o crédito); estimativa do ganho comercial do cliente; calendário da opção semestral do CGSN.
8. ✅ *(v0.2.0; falta IRPF anual e efeito nos dividendos)* **Otimizador de pró-labore e Fator R.** Sugerir o pró-labore que minimiza DAS + INSS (11% do sócio; 20% patronal fora do Simples) + IRPF do sócio.

### P2 — Escala no escritório

9. ✅ *(v0.2.0)* **Painel da carteira.** Rodar todos os clientes e listar quem deveria mudar de regime antes de janeiro (a opção é irretratável no ano), com economia estimada. Gerar em novembro/dezembro.
10. **Planejado × realizado.** Guardar cada planejamento e comparar com o mês fechado seguinte (erro da projeção, mudança de regime sugerida).
11. ✅ *(v0.2.0; falta alerta por e-mail/agenda)* **Prazos e calendário.** Alertas da opção do Simples (último dia útil de janeiro), da opção semestral pelo IBS/CBS e da fixação anual da alíquota da CBS.
12. **Pasta de dados na rede** (ex.: `Z:\...`) com trava simples de edição, backup e log de quem importou e gerou cada relatório (LGPD e rastreabilidade).

### P2 — Cobertura de regras

13. Segregação de **ICMS-ST, monofásicos e exportação** no Simples (CFOP/CST/NCM das saídas).
14. **Presunções específicas por atividade** no Presumido (transporte, hospitalar etc.), por CNAE ou acumulador.
15. **Crédito sobre imobilizado** no Real (depreciação) e na CBS/IBS (na aquisição, já marcado no De-Para).
16. ✅ *(v0.2.0)* **Sublimite exato** pela receita acumulada no ano e regra do mês de ultrapassagem.
17. **Regras com vigência por data** (tabelas versionadas em CSV/YAML com "válido de/até"), para recalcular períodos antigos com a regra da época.

### P3 — Distribuição e manutenção

18. **Instalador .exe** (PyInstaller) e botão "Atualizar sistema" (git pull + reinstalação).
19. **Fixtures anonimizadas dos layouts reais do Domínio** no repositório, para o CI cobrir mudanças de layout.
20. **Leitura direta do banco do Domínio** (ODBC/consulta): avaliar viabilidade e licença antes de qualquer código.

---

## 7. Próxima tarefa sugerida

A v0.2.0 entregou os itens 6, 8, 9, 11 e 16. Seguir pelos itens **1 e 2**: o "DAS calculado × DAS pago" valida todo o resto, e a DRE mensal corrige a maior fonte de distorção do Lucro Real.

Antes de codificar:
- me peça um extrato do PGDAS-D e DREs mensais de exemplo, exportados do Domínio;
- não presuma o layout desses arquivos.
