# AGENTS.md — briefing para agentes de código (Codex e outros)

> Leia este arquivo inteiro antes de mexer em qualquer coisa. Ele resume o projeto, as regras do repositório,
> os pontos fracos conhecidos e a **tarefa paralela** reservada para você. O Claude Code trabalha neste mesmo
> repositório ao mesmo tempo: respeite a divisão de arquivos da seção 9.

---

## 1. O que é

**Zera Planejamento Tributário** — sistema interno da **Zera Contabilidade** (escritório em São Paulo que usa o
Sistema Domínio). Faz planejamento tributário mensal com projeção semestral:

1. Lê relatórios exportados do Domínio (.xls): Acompanhamento de Serviços/Saídas/Entradas, Extrato Mensal da
   folha e D.R.E.
2. Monta a **base mensal** do cliente (receita por anexo, base de crédito, folha, custos, despesas).
3. Calcula mês a mês **Simples Nacional**, **Simples híbrido** (IBS/CBS por fora, a partir de 2027),
   **Lucro Presumido** e **Lucro Real**, com as regras de 2026 e a transição da Reforma Tributária até 2033.
4. Projeta 6 meses em 3 cenários (Neutro por tendência, Otimista +15%, Pessimista −15%).
5. Mostra o regime de menor carga, pontos de equilíbrio, carga sócio + empresa (Lei 15.270/2025), pró-labore
   ótimo, prazos de decisão e alertas.
6. Entrega dashboard interativo (Streamlit), Excel auditável e PDF com a identidade visual da Zera.

**Quem usa:** a equipe do escritório (não programa), no Windows, pelo navegador.
**Natureza do resultado:** rascunho técnico para o contador revisar. Nunca prometer resultado fiscal.

Repositório: `github.com/ZeraContabilidade/zera-planejamento` (privado). Branch principal: `main`.
Versão atual: **0.6.1**. Histórico em `CHANGELOG.md`; especificação viva e roadmap em `PROMPT.md`.

---

## 2. Como rodar

```bash
python -m pip install -e .[dev]      # Python 3.11+ (local usa 3.13; CI roda 3.11 e 3.12, Windows e Ubuntu)
python -m pytest                     # 91 testes; 2 são pulados sem amostras/cs_geartech (dados reais, fora do git)
zera-planejamento app                # abre o Streamlit (roda dentro de src/zera_planejamento/app/ p/ ler o tema)
zera-planejamento carteira           # painel de todos os clientes no terminal
```

- Dados de clientes ficam fora do git, em `C:\ZeraPlanejamento\dados` (variável `ZERA_DADOS`). Para testar o app,
  crie uma pasta temporária e aponte `ZERA_DADOS` para ela.
- O teste do app (`tests/test_fluxo.py::test_app_todas_as_paginas`) usa `streamlit.testing.AppTest` e leva ~1 min.
- O primeiro planejamento de um cliente leva ~20 s (ver seção 7, desempenho).

---

## 3. Arquitetura (src/zera_planejamento)

| Módulo | Responsabilidade |
|---|---|
| `regras/` | **Única fonte de regras tributárias**, com base legal no docstring. `simples.py` (anexos, RBT12 2026×2027, sublimite, partilha ICMS/ISS), `federais.py` (Presumido, LC 224/2025, Real, encargos), `reforma.py` (CBS/IBS 2026–2033, partilha do Simples), `pessoa_fisica.py` (INSS/IRRF 2026, Lei 15.270: dividendos e IRPFM), `dados/*.csv` (tabelas de partilha). `pendencias_conferir()` lista o que é `[CONFERIR]`. |
| `base.py` | Base mensal canônica (`COLUNAS`), origem de cada valor, CSV, planilha de digitação. |
| `cliente.py` | Cadastro (`Cliente`, `Socio`, `Projecao`), pastas, regras efetivas por cliente. |
| `dominio/` | Leitura dos .xls do Domínio (python-calamine), reconhecimento por título, De-Para, importação com alertas e conferências cruzadas; `generico.py` lê qualquer Excel/CSV/PDF (pdfplumber) e aplica o mapa de rótulos do cliente. |
| `calculo/` | **Motor único** (fonte oficial dos números): `comum.py`, `simples.py`, `presumido.py`, `real.py`, `motor.py` (`calcular`, `Resultado.resumo`, `simular_transicao`). |
| `projecao.py` | 3 cenários; o cálculo roda na série histórico + projeção. |
| `equilibrio.py` | Break-even (margem, faturamento, Fator R) e curva de sensibilidade — o passo mais lento. |
| `planejamento.py` | Fluxo completo → `Planejamento` (histórico, cenários, resumo, equilíbrio, transição, sócios, prazos, alertas). |
| `socios.py` | Visão sócio + empresa (Lei 15.270) e otimizador de pró-labore/Fator R. |
| `prazos.py` | Calendário de decisões (dias úteis, feriados nacionais). |
| `carteira.py` | Painel: roda todos os clientes e classifica MUDAR / AVALIAR / MANTER. |
| `painel.py` | Dados do dashboard (recorte por cenário e período, indicadores). |
| `consulta_cnpj.py` | Dados abertos do CNPJ (BrasilAPI, reserva CNPJ.ws) e validação de dígitos. |
| `relatorio/` | Gráficos PNG (matplotlib), Excel com gráficos nativos (openpyxl), PDF (ReportLab, timbrado). |
| `app/` | Streamlit: `main.py`, `estado.py` (cache do planejamento), `visual.py` (identidade Zera), `.streamlit/config.toml` (tema), `static/` (logo e fontes), `paginas/` (dashboard, cadastro, importar, base, planejamento, socios, relatorios, carteira, depara, configuracoes). |
| `cli.py` | `zera-planejamento app | clientes | importar | relatorio | carteira`. |

Fluxo: `dominio.importar_relatorios` → `BaseMensal` → `planejamento.gerar_planejamento` (→ `calculo.calcular`
várias vezes) → telas / `relatorio.gerar_relatorios`.

---

## 4. Regras tributárias implementadas (resumo — detalhe e base legal em `docs/regras-tributarias.md`)

- **Simples (LC 123/2006):** Anexos I–V, Fator R 28%; RBT12/FS12 dos 12 meses anteriores até 12/2026 e, desde
  01/2027, dos 12 meses antecedentes ao mês anterior (LC 214/2025); sublimite de R$ 3,6 mi pela receita do ano
  anterior e acumulada (excesso > 20% → mês seguinte), com DAS sem a parcela de ICMS/ISS; exclusão acima de
  R$ 4,8 mi; Anexo IV com CPP fora; híbrido 2027+ (DAS sem CBS/IBS + CBS/IBS não cumulativos por fora).
- **Presumido:** presunção por anexo; LC 224/2025 (+10% acima de R$ 1,25 mi/tri, ajuste anual a R$ 5 mi; IRPJ desde
  01/2026, CSLL desde 04/2026); IRPJ/CSLL trimestrais; PIS/Cofins cumulativos até 2026 (Tema 69); CBS/IBS 2027+.
- **Real:** PIS/Cofins não cumulativos com crédito sem ICMS (Lei 14.592/23); receitas financeiras 4,65%;
  compensação de prejuízo até 30%, trimestral ou anual.
- **Reforma:** CBS/IBS de teste em 2026 (sem custo); 2027–28 CBS referência − 0,1 p.p. e IBS 0,1%; 2029–32 IBS
  10%–40% e ICMS/ISS reduzidos; 2033 pleno. Referências editáveis (CBS 9,21%, IBS 18,7%).
- **Pessoa física (2026):** INSS 11% até o teto R$ 8.475,55; IRRF Lei 15.191/2025 com a redução da Lei 15.270/2025;
  lucros > R$ 50 mil/mês por sócio e empresa → IRRF 10% sobre o total; IRPFM acima de R$ 600 mil/ano (10% a partir
  de R$ 1,2 mi) com redutor PJ + PF até 34%.
- **Pendências `[CONFERIR]`** (aparecem na tela e no PDF): ver `regras.pendencias_conferir()`.

---

## 5. Regras do repositório (obrigatórias)

- Código, nomes, mensagens e commits **em português**. Valores com `formatos.brl` / `formatos.pct` / `formatos.brl_curto`.
- **Regra tributária só em `regras/`**, com base legal (lei, artigo, IN) no docstring. Nunca inventar alíquota, prazo
  ou caminho de menu do Domínio. Na dúvida, marcar `[CONFERIR]` e incluir em `pendencias_conferir()`.
- O motor (`calculo/`) é a única fonte dos números; telas e relatórios só exibem.
- **Todo cálculo novo ou alterado tem teste com memória de cálculo nos comentários** (ver `tests/test_calculo.py`).
- `tests/test_validacao_casos.py` traz empresas fictícias calculadas à mão com a memória completa: use como referência
  e não altere os valores esperados sem base legal.
- A regressão da CS Geartech (`tests/test_regressao_cs_geartech.py`) precisa continuar batendo — Presumido
  R$ 284.704,68, Simples R$ 237.945,88, Real R$ 574.294,06 (jan–set/2026). Ela só roda onde há `amostras/`; se sua
  mudança puder alterar esses números, **explique no PR** e peça para rodar localmente.
- **Nunca versionar dados de cliente** (`amostras/`, `dados/`, `.xls`, `.xlsx`, `.pdf` estão no `.gitignore`).
  Testes usam relatórios sintéticos no layout do Domínio (`tests/conftest.py`).
- Streamlit: páginas em `app/paginas/`; `width="stretch"`; texto com R$ em `st.markdown`/`st.info` passa por
  `estado.md()` (senão "R$ … R$" vira fórmula LaTeX).
- Trabalhe em **branch própria** e abra **PR para `main`**; não faça push direto na `main`. O token usado no
  computador do escritório não tem escopo `workflow`: alterações em `.github/workflows/` precisam ser feitas por você.
- Ao terminar: diga o que mudou, como testou e o próximo passo.

---

## 6. Histórico

| Versão | Conteúdo |
|---|---|
| 0.1.0 | Motor refeito do zero, importação do Domínio, projeção, equilíbrio, Excel e PDF. |
| 0.2.0 | Sócio + empresa (Lei 15.270), pró-labore ótimo, sublimite exato, painel da carteira, prazos. |
| 0.3.0 | Identidade visual Zera no app, dashboard interativo, cache do planejamento entre telas. |
| 0.4.0 | Cadastro pelo CNPJ (dados abertos da RFB), correções no cadastro (sócios apagados, modo novo cliente). |
| 0.5.0 | Parecer ao cliente (Word + PDF), casos de validação calculados à mão, roteiro do cliente na navegação. |
| 0.5.1 | Revisão crítica e otimização do motor (Codex, PR #6): redutor do IRPFM conforme o art. 16-B, motor ~10× mais rápido. |
| 0.6.0 | Importação de qualquer documento financeiro (Excel, CSV, PDF) com mapa de rótulos por cliente. |

---

## 7. Pontos fracos conhecidos — onde olhar com olhar crítico

Lista honesta do autor (Claude Code). Confirme, refute ou amplie; não aceite nada daqui sem verificar.

**Corretude / regras**
1. `regras/dados/simples_partilha_icms_iss.csv`: percentuais de ICMS/ISS por faixa (2026) transcritos dos Anexos da
   LC 123 sem conferência linha a linha com o texto legal. ISS limitado a 5% nas 5ªs faixas dos Anexos III/IV.
2. `calculo/simples.py`: RBT12 na 6ª faixa sem impedimento pelo sublimite leva ICMS/ISS para fora (Res. CGSN 140,
   art. 25, não implementado). Sublimite do ano anterior é proporcionalizado pela média dos meses informados.
3. `calculo/simples.py`: no mês impedido, `das_cbs`/`das_ibs` (híbrido) usam o DAS cheio antes de tirar ICMS/ISS —
   conferir se está certo para o híbrido.
4. `socios.py`: lucro contábil = receita + rec. financeiras − custos − despesas − folha − (tributos − CBS/IBS por
   fora); IRPFM anualizado a partir dos 6 meses projetados; alíquota efetiva da PJ no Simples = 0 (superestima o
   IRPFM); distribuição "mensal" assume valores iguais por mês; não modela lucros de anos anteriores.
5. `socios.otimizar_pro_labore`: supõe regime estabilizado (pró-labore igual nos 12 meses), ignora o efeito sobre
   dividendos, grade de 21 pontos, `meses_ate_anexo_iii` é estimativa linear.
6. `regras/pessoa_fisica.py`: tabelas de 2026 fixas no código (sem vigência por data); IRRF mensal, sem ajuste anual.
7. `prazos.py`: feriados só nacionais fixos + Sexta-feira Santa (sem Carnaval, Corpus Christi, municipais); data de
   15/12/2026 da CBS e opção semestral do híbrido (LC 214, art. 41) estão `[CONFERIR]`.
8. `carteira.py`: usa só o cenário Neutro e a projeção de 6 meses (que mistura regras de 2026 e 2027) anualizada × 2.
9. `consulta_cnpj.py`: regime sugerido pela última forma de tributação declarada pode estar desatualizado; QSA não
   traz percentuais; BrasilAPI devolve município sem acento.
10. `projecao.py`: tendência linear pode explodir/zerar com poucos meses; itens fixos = média dos últimos 3 meses.

**Engenharia**
11. ~~**Desempenho**~~ resolvido na 0.5.1 (planejamento ~4 s). Histórico: `calculo.calcular` levava ~0,5 s para ~21 meses (overhead de pandas com `PeriodIndex`, `ratear`,
    `clip`, `__getitem__` em laço); `equilibrio.pontos_equilibrio` chama o motor dezenas de vezes (~18 s);
    `gerar_planejamento` completo ~30 s.
12. `app/estado.py`: `st.cache_resource` compartilha o objeto `Planejamento` entre sessões e o muta (anexa o
    equilíbrio) — avaliar concorrência; chave = sha1 do cadastro + CSV da base.
13. Páginas Streamlit com linhas > 120 colunas e lógica de exibição extensa (`dashboard.py`, `cadastro.py`).
14. Empacotamento: `app/.streamlit/config.toml` e `app/static/` no `package-data` — só testado com instalação
    editável (`pip install -e`).
15. Cobertura: leitores do Domínio testados só com layouts sintéticos; sem teste de PDF além do tamanho; sem
    teste de erro de rede no app.

---

## 8. O que entregar na revisão crítica

Crie `docs/REVISAO-CODEX.md` com uma tabela de achados, do mais grave para o menos grave:

| # | Gravidade (CRÍTICO/ALTO/MÉDIO/BAIXO) | Arquivo:linha | Problema | Cenário que falha (entrada → saída errada) | Correção proposta | Base legal (se for regra) |

- Separe **erro de regra tributária** (precisa de base legal) de **erro de código**.
- Para cada achado CRÍTICO/ALTO, escreva um **teste que falha** antes da correção.
- Não "corrija" regra tributária sem citar a lei/IN; se discordar de uma regra, marque `[CONFERIR]` e explique.

---

## 9. Tarefa paralela para o Codex (sem conflito com o Claude Code)

O Claude Code continua trabalhando em `app/`, `consulta_cnpj.py`, `dominio/` e na documentação. Para não haver
conflito, **a sua área é o motor e o desempenho**:

**Branch:** `codex/revisao-motor` → PR para `main`.

**Arquivos que você pode alterar:** `src/zera_planejamento/calculo/`, `equilibrio.py`, `projecao.py`,
`socios.py`, `regras/` (só com base legal), `tests/test_calculo.py`, `tests/test_socios_prazos.py`, novos testes
em `tests/`, e `docs/REVISAO-CODEX.md`. **Não altere** `app/`, `dominio/`, `consulta_cnpj.py`, `relatorio/`,
`README.md`, `PROMPT.md`, `CHANGELOG.md` (o Claude Code consolida o CHANGELOG ao integrar).

**Objetivos, em ordem:**
1. **Revisão crítica** do motor e de `socios.py`/`projecao.py` (seção 8), com testes que reproduzem cada erro.
2. **Desempenho sem mudar nenhum número:** levar `calcular` de ~0,5 s para < 0,1 s e `gerar_planejamento` completo
   para < 8 s em uma base de 21 meses (ex.: usar arrays NumPy dentro dos laços, evitar `Series.__getitem__`/`clip`
   repetidos, `ratear` vetorizado, reaproveitar cálculos entre as chamadas do break-even).
   - Antes de otimizar, grave um **teste de "foto"** (golden) com os resultados atuais de `calcular` e
     `gerar_planejamento` para as bases de `tests/conftest.py` e de `tests/test_calculo.py`, e garanta igualdade
     (tolerância de R$ 0,01) depois da otimização.
   - Reporte os tempos antes/depois no PR.
3. Corrigir os achados CRÍTICO/ALTO que estiverem dentro da sua área.

**Critérios de aceite:** `python -m pytest` verde; nenhum número da foto alterado (ou alteração justificada com
base legal); tempos medidos no PR; nada de dados de cliente no commit.
