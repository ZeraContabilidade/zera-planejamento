# Histórico de versões

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
