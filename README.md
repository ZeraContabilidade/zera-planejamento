# Zera Planejamento Tributário

Planejamento tributário mensal com projeção semestral para os clientes da **Zera Contabilidade**.

- **Entrada:** relatórios exportados do **Domínio** (serviços, saídas, entradas, extrato da folha e DRE).
- **Outros documentos:** qualquer planilha (Excel, CSV) ou PDF com texto, ligando cada linha a um item da base (o sistema lembra as escolhas por cliente).
- **Comparação:** **Simples Nacional**, **Simples híbrido** (IBS/CBS por fora), **Lucro Presumido** e **Lucro Real**, mês a mês, com as regras de 2026 e a transição da Reforma até 2033.
- **Projeção:** próximos 6 meses em três cenários.
- **Sócios:** carga sócio + empresa com a Lei 15.270/2025 (lucros acima de R$ 50 mil/mês e IR mínimo) e pró-labore ótimo / Fator R.
- **Escritório:** painel da carteira (quem deveria mudar de regime antes de janeiro) e prazos de decisão.
- **Dashboard:** recomendação, indicadores e gráficos interativos por cenário, com a identidade visual da Zera.
- **Comparação entre anos:** realizado de cada ano, mesmo período (ex.: jan–set) e projeção do próximo ano em cenários.
- **Mesa do escritório e Simulador “E se…”:** a carteira de relance e o imposto de cada regime recalculado ao vivo.
- **Reforma Tributária 2026–2033 e precisão:** o cliente ano a ano na transição, regime diferenciado do IBS/CBS e diagnóstico do que falta para números mais precisos.
- **Saída:** regime de menor carga, pontos de equilíbrio e alertas, com relatórios em Excel e PDF no padrão Zera.

> Resultado é **rascunho técnico**: o contador revisa antes de levar ao cliente.

## Instalação (Windows, uma vez por computador)

1. Instale o **Python 3.11 ou superior** em python.org e marque **"Add python.exe to PATH"**.
2. Copie esta pasta para `C:\ZeraPlanejamento\sistema` (ou clone com o GitHub Desktop).
3. Dê dois cliques em **`instalar.bat`**.

## Uso

1. Dê dois cliques em **`Iniciar Zera Planejamento.bat`**. O sistema abre no navegador.
2. **Cadastro:** crie o cliente — digite o CNPJ e clique em **Buscar na Receita** para preencher os dados — e confira ISS, RAT/FAP/Terceiros e o anexo dos serviços.
3. **Importar Domínio:** envie os relatórios (o .xls do Domínio, sem converter), leia os alertas e clique em **Gravar**.
4. **Base mensal:** complete o que não vem do Domínio (aluguel, histórico anterior, ajustes do LALUR).
5. **Dashboard:** veja a recomendação, os indicadores e os gráficos; troque o cenário e o período nos filtros.
   Para o detalhe (equilíbrio, tabelas), abra **Planejamento**.
6. **Sócios e pró-labore:** cadastre os sócios, veja a carga sócio + empresa e calcule o pró-labore ótimo.
7. **Relatórios:** gere o Excel e o PDF.
8. **Painel da carteira** (novembro/dezembro): rode todos os clientes e veja quem deveria mudar de regime.

Os dados ficam em `C:\ZeraPlanejamento\dados` (fora do repositório). O manual completo está em [`docs/manual-equipe.md`](docs/manual-equipe.md).

## Relatórios do Domínio

| Relatório | Módulo | Para quê |
|---|---|---|
| Acompanhamento de Serviços / de Saídas | Escrita Fiscal | receita por anexo |
| Acompanhamento de Entradas | Escrita Fiscal | base de crédito por CFOP |
| Extrato Mensal (Folha Mensal e Complementar) | Folha | salários, pró-labore, FGTS |
| D.R.E. (de preferência uma por mês) | Contabilidade | custos, despesas e resultado |

Exporte desde **janeiro do ano anterior** para a RBT12 sair exata.

## Desenvolvimento

```bash
python -m pip install -e .[dev]
python -m pytest
zera-planejamento app
zera-planejamento carteira --excel painel.xlsx
```

- Especificação, decisões e roadmap: [`PROMPT.md`](PROMPT.md).
- Regras e base legal: [`docs/regras-tributarias.md`](docs/regras-tributarias.md).
- Convenções para o Claude Code: [`CLAUDE.md`](CLAUDE.md).

Uso interno — Zera Contabilidade.
