# Histórico de versões

## 0.7.0 — 26/10/2026
**Comparação entre anos** — nova tela em Análise
- Realizado de cada ano, estimativa de fechamento do ano corrente (meses reais + estimados) e projeção do próximo ano
  (12 meses), todos pelo motor na série inteira: RBT12, trimestres, prejuízo e regras de cada ano (CBS/IBS e RBT12
  sem o mês anterior a partir de 2027).
- Comparação no mesmo período (ex.: jan–set/2025 × jan–set/2026): receita e tributos por regime, diferença e variação.
- Base da projeção: tendência ou média dos últimos 12 meses, ou média + crescimento informado (padrão: o crescimento
  observado no mesmo período). Cenários Pessimista/Central/Otimista com variação ajustável.
- Destaque do próximo ano (regime de menor carga e economia sobre o atual), gráficos de tributos por ano e de receita
  mês a mês por ano, resumo anual, cenários e exportação em Excel.
- Ano com meses reais sem DRE não mostra o Lucro Real (sairia sobre lucro ≈ receita) e avisa; o Simples híbrido só
  aparece a partir de 2027. Primeiro ano parcial não entra na variação.
- 6 testes com memória de cálculo (crescimento informado, mesmo período, cenários, meses por tipo, ano parcial, ano
  sem DRE). Conferido também com os dados reais da CS Geartech (local).

## 0.6.1 — 23/10/2026
**Validação com os relatórios reais da CS Geartech (jan–set/2026)**
- Regressão confirmada no centavo depois da otimização do motor: Presumido R$ 284.704,68, Simples R$ 237.945,88,
  Real R$ 574.294,06. O teste agora aceita o nome do arquivo como o Domínio exporta (`Serviços.xls`, com acento).
- A importação livre ("Outros documentos") lendo o relatório de Serviços do Domínio chega à mesma receita oficial
  (R$ 1.702.112,28) — teste local, só roda onde estão as amostras.

**Importação livre — correções achadas com os arquivos reais**
- Linhas com tamanhos diferentes travavam a detecção (erro de índice).
- DRE/balancete: o rótulo passa a ser o primeiro texto à esquerda dos valores (as contas mudam de coluna conforme o
  nível) e a coluna de valor é a de saldo analítico, mais à esquerda, para não somar subtotais.
- Nome das colunas pelo título mais próximo dos dados; competência sugerida pela data do título e aviso quando o
  documento é acumulado no exercício.
- "-R$ 0,00" em diferenças de frações de centavo passa a aparecer como "R$ 0,00".

## 0.6.0 — 23/10/2026
**Importação de qualquer documento financeiro (Excel, CSV e PDF)** — nova tela "Outros documentos"
- Lê todas as abas de planilhas (.xlsx, .xlsm, .xls, .ods, .csv) e as tabelas de PDFs com texto (com ou sem grade;
  sem grade, números e meses são separados do rótulo pela direita). PDF digitalizado (imagem) é recusado com aviso.
- Encontra os meses sozinho: em colunas (jan/26, 01/2026, 2026-01, datas) ou numa coluna de datas; documento de um
  período pede a competência. Valores acumulados no ano viram mensais pela diferença.
- O usuário liga cada rótulo a um item da base (sugestões automáticas: receita, custos, salários, pró-labore, FGTS,
  devoluções, receitas financeiras; totais e lucro em "ignorar"). As escolhas ficam salvas no cliente
  (`mapa_rotulos`) e voltam prontas no próximo documento.
- Prévia do que será gravado, aviso de valores que serão substituídos, original guardado em `importacoes/`.
- `pdfplumber` como dependência.

**Testes:** 8 novos com documentos sintéticos (Excel acumulado, CSV, PDF texto e grade, PDF sem texto, mapa do cliente,
tela do envio à gravação). A foto do motor aceita campos novos e vazios no cadastro, sem afrouxar a comparação dos valores.

## 0.5.1 — 23/10/2026
Integra a revisão crítica e a otimização do motor feitas pelo Codex (PR #6; relatório em `docs/REVISAO-CODEX.md`).

**Correções de regra (Lei 9.250/1995, art. 16-B, incluído pela Lei 15.270/2025)** — conferidas no texto oficial
- Alíquota efetiva da PJ para o redutor do IRPFM = IRPJ + CSLL ÷ lucro contábil **antes** desses tributos (§ 3º, I e III).
- Alíquota efetiva do IRPFM = acréscimo do imposto mínimo causado pelos dividendos ÷ dividendos (§ 3º, II), em vez da
  alíquota nominal da tabela.

**Correções de código**
- Sazonalidade com mês sem receita não gera mais projeção vazia (NaN).
- Break-even não confunde regime indisponível com ponto de equilíbrio.
- Resumo de um período sem meses não recomenda regime; visão dos sócios sem meses não divide por zero.

**Desempenho:** `calcular` de ~1,3 s para ~0,09 s; planejamento completo de ~45 s para ~4 s (conferido nesta máquina),
sem mudar nenhum imposto da empresa: teste "foto" com 12 casos e tolerância de R$ 0,01.

**Pendências registradas pelo Codex (MÉDIO):** meses sem DRE tratados como custo zero; anualização da visão dos sócios;
sublimite com histórico parcial do ano anterior; referência do otimizador de pró-labore. Ver `docs/REVISAO-CODEX.md`.

## 0.5.0 — 23/10/2026
**Parecer ao cliente (Word + PDF)** — item 5 do roadmap
- Uma página em linguagem simples, com o timbrado da Zera: recomendação, economia ou carga estimada, prazo de decisão,
  tabela dos regimes por ano, o que muda na prática, pontos de atenção (Fator R, Lei 15.270, Reforma) e próximo passo.
- Word no layout do modelo `zera_doc.js` do kit (faixa do timbrado, rótulos dourados, cartões 01-02-03, rodapé com
  página) e com as fontes Cormorant Garamond e Inter embutidas; PDF equivalente. Conferido no Microsoft Word.
- Tela Relatórios reorganizada: "Para o cliente" (parecer) e "Uso interno" (Excel e PDF técnico); downloads por cliente.

**Validação do planejamento**
- `tests/test_validacao_casos.py`: 9 empresas fictícias calculadas à mão pela lei (Simples Anexos I e III, Presumido
  com LC 224 e adicional do IRPJ, Real com prejuízo e trava de 30%, CBS/IBS 2027, coerência dos cenários). O motor
  bate em todos.

**Navegação**
- Roteiro do cliente na barra lateral (cadastro com CNPJ, relatórios do Domínio, 13 meses de receita, DRE, sócios,
  parecer), com atalho para cada etapa e o próximo passo em destaque.
- Dashboard sem base mostra o guia de início; depois de salvar o cadastro ou importar, links para o passo seguinte.

## 0.4.0 — 23/10/2026
**Cadastro pelo CNPJ (dados abertos da Receita Federal)**
- Botão **Buscar na Receita** no Cadastro: preenche razão social, CNPJ, município, UF e atividade (CNAE).
- Sugere o regime atual: optante do Simples ou a última forma de tributação declarada (Lucro Real/Presumido).
- Mostra situação cadastral, opção pelo Simples/MEI, porte, CNAEs secundários e o quadro de sócios. Também oferece
  cadastrar os sócios pessoa física (participação igual, para ajustar depois).
- Fontes: BrasilAPI e, de reserva, CNPJ.ws (só o número do CNPJ sai do computador). Valida os dígitos do CNPJ antes.
- Avisos para empresa não ativa e para MEI.

**Correções**
- Salvar o Cadastro não apaga mais os sócios cadastrados.
- O modo "Novo cliente" continua ativo até salvar (antes, qualquer clique voltava para o cliente da barra lateral).

## 0.3.0 — 23/10/2026
**Identidade visual da Zera no sistema**
- Tema do kit "ZERA - IDENTIDADE VISUAL": barra lateral preta com a logo dourada, dourado #C5A15F / #A8843F,
  títulos em Cormorant Garamond e texto em Inter (fontes e logo dentro do sistema, funcionam sem o Drive).
- Cabeçalho de todas as telas no padrão do timbrado (rótulo dourado, título em Cormorant, diagonal dourada com a logo).

**Dashboard do cliente** (nova tela inicial)
- Faixa de recomendação (mudar ou manter, economia por ano e prazo de decisão).
- Cartões: menor carga, economia por ano, carga efetiva, receita, Fator R ou vantagem sobre o 2º, próximo prazo.
- Filtros de cenário (Neutro, Otimista, Pessimista), período (projeção ou últimos 12 meses) e regimes exibidos.
- Gráficos interativos: ranking dos regimes, composição por tributo (clique na legenda destaca), evolução mês a mês
  com histórico e projeção, receita × carga efetiva, Fator R com a linha de 28%, transição 2026–2033.
- Prazos de decisão e alertas no mesmo painel.

**Velocidade**
- O planejamento fica guardado entre telas e sessões; o break-even só é calculado na tela Planejamento e nos relatórios
  (o dashboard abre em cerca de metade do tempo). Janela da RBT12 calculada com arrays.

## 0.2.0 — 23/10/2026
Melhorias do roadmap que não dependem de novos layouts do Domínio.

**Sócio + empresa (Lei 15.270/2025)**
- Cadastro de sócios (participação, pró-labore, dependentes e outras rendas) e da política de distribuição.
- Carga total por regime: tributos da empresa + INSS e IRRF do pró-labore + IRPFM sobre os lucros, com redutor de 34%.
  IRRF de 10% sobre lucros acima de R$ 50 mil/mês mostrado como antecipação. Avisa quando a recomendação muda.
- Tabelas de 2026 da pessoa física: INSS 11% até o teto, IRRF (Lei 15.191/2025) com a redução da Lei 15.270/2025.

**Pró-labore ótimo e Fator R**
- Testa valores de pró-labore e mostra, por regime, o de menor custo (empresa + INSS + IRRF dos sócios), o valor que
  leva o Fator R a 28% e em quantos meses o Anexo III passa a valer.

**Simples — sublimite exato**
- Impedimento de ICMS/ISS no DAS pela receita do ano anterior e pela acumulada no ano (excesso acima de 20% → mês
  seguinte), com o DAS sem a parcela de ICMS/ISS da repartição (LC 123, art. 20, §§ 1º e 1º-A).

**Escritório**
- Painel da carteira (tela e `zera-planejamento carteira`): quem deveria mudar de regime antes de janeiro, com economia
  anual estimada e prazo de decisão.
- Prazos de decisão (opção/exclusão do Simples, Presumido, Real, opção semestral do híbrido, alíquota da CBS) na tela,
  no Excel e no PDF.

**Relatórios e qualidade**
- Excel com as abas "Sócios e empresa" e "Prazos"; PDF com as seções correspondentes.
- 39 testes (12 novos, com memória de cálculo). Correção: valores em R$ no texto das telas saíam formatados como fórmula.

## 0.1.0 — 23/10/2026
Primeira versão, refeita do zero.

**Cálculo**
- Motor único em Python: Simples (por dentro e híbrido), Presumido (LC 224/2025) e Real.
- Reforma 2026–2033 e simulação da transição.
- RBT12/FS12 com a regra de 2027 (mês anterior fora da janela).
- Créditos separados: PIS/Cofins × CBS/IBS (uso e consumo e imobilizado só na CBS/IBS).
- Compensação de prejuízo entre trimestres.

**Importação do Domínio**
- Serviços, Saídas, Entradas, Extrato Mensal e DRE, com De-Para por cliente.
- Alertas e conferências cruzadas: receita das notas × DRE, folha × DRE, prestador que já foi empregado, conta genérica, aluguel sem DRE.

**Projeção e relatórios**
- Projeção de 6 meses em 3 cenários e pontos de equilíbrio (margem, faturamento, Fator R).
- Excel com gráficos nativos e PDF com a identidade da Zera.

**Uso e qualidade**
- Tela no navegador (Streamlit), linha de comando e scripts Windows.
- 27 testes, incluindo a regressão real da CS Geartech (local).
