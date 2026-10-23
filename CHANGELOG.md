# Histórico de versões

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
